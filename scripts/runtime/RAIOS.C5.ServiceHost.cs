using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.ServiceProcess;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Security.Cryptography;

namespace RAIOS.ControlPlane
{
    public sealed class C5Service : ServiceBase
    {
        const string ServiceNameConst = "RAIOS-C5";
        static readonly string Root = @"C:\Users\Ghanam\.raios\runtime\continuity\c5-service";
        static readonly string StatePath = Path.Combine(Root, "state.json");
        static readonly string WalPath = Path.Combine(Root, "wal.jsonl");
        static readonly string GenerationStatePath = Path.Combine(Root, "current-generation.json");
        static readonly string GenerationReceiptPath = Path.Combine(Root, "generation-promotion-receipt.json");
        static readonly string BrokerRequest = @"C:\Users\Ghanam\.raios\runtime\continuity\privileged-exec\CURRENT.request.json";
        static readonly string BrokerScript = @"C:\Users\Ghanam\.raios\runtime\continuity\privileged-exec\Invoke-RAIOS-Privileged-Broker.ps1";
        static readonly string UserLaneScript = Path.Combine(Root, "Invoke-RAIOS-C5-UserLane.ps1");
        static readonly string MaintainScript = @"C:\Users\Ghanam\Documents\Codex\Greeny-Life\scripts\runtime\Maintain-RAIOS-Online.ps1";
        static readonly string PowerShell = @"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe";
        static readonly string Python = @"C:\Users\Ghanam\AppData\Local\Programs\Python\Python314\python.exe";
        static readonly string DcrSupervisor = @"C:\Users\Ghanam\.raios\runtime\continuity\reap_stale_rdc_sessions.py";
        static readonly string DcrStatePath = @"C:\Users\Ghanam\.raios\runtime\remote-access\rdc-system-direct\rdc-supervisor-state.json";
        static readonly string StableUserProfile = @"C:\Users\Ghanam";
        static readonly string DcrState = @"C:\Users\Ghanam\.raios\runtime\remote-access\rdc-system-direct\rdc-supervisor-state.json";
        static readonly string TunnelClient = @"C:\Users\Ghanam\.raios\runtime\mcp-tunnel\bin\tunnel-client.exe";
        static readonly string TunnelLauncher = @"C:\Users\Ghanam\.raios\runtime\mcp-tunnel\Start-RAIOS-Native-MCP-System.ps1";
        static readonly string TunnelProfileDir = @"C:\Users\Ghanam\.raios\runtime\mcp-tunnel\profiles";
        static readonly string TunnelHealthUrlFile = @"C:\Users\Ghanam\.local\state\tunnel-client\health\raios-native.url";
        static readonly string TunnelOwnerState = @"C:\Users\Ghanam\.raios\runtime\mcp-tunnel\health\raios-native.owner.json";
        static readonly string TunnelMachineSecret = @"C:\Users\Ghanam\.raios\runtime\mcp-tunnel\secrets\control-plane-api-key.machine.dpapi";
        static readonly string TunnelTokenStore = @"C:\Users\Ghanam\Documents\Codex\Greeny-Life\.ai-os\mcp\tokens.local.json";
        const string TunnelProfile = "raios-native";
        static readonly string Repo = @"C:\Users\Ghanam\Documents\Codex\Greeny-Life";

        readonly ManualResetEvent stop = new ManualResetEvent(false);
        Thread worker;
        IntPtr job = IntPtr.Zero;
        int userLanePid = 0;
        int dcrSupervisorPid = 0;
        int nativeTunnelPid = 0;
        int nativeTunnelLauncherPid = 0;
        DateTime nativeTunnelLauncherStartedUtc = DateTime.MinValue;
        int nativeTransportFailureCount = 0;
        DateTime nativeTransportFailureSinceUtc = DateTime.MinValue;
        int nativeLaunchFailureCount = 0;
        int headlessRepairPid = 0;
        DateTime dcrRetryAfterUtc = DateTime.MinValue;
        DateTime tunnelRetryAfterUtc = DateTime.MinValue;
        DateTime userLaneRetryAfterUtc = DateTime.MinValue;
        DateTime headlessRepairRetryAfterUtc = DateTime.MinValue;
        DateTime headlessRepairStartedUtc = DateTime.MinValue;
        uint userLaneSession = 0xFFFFFFFF;
        string lastHash = "";
        string generationId = "";
        string generationBinaryHash = "";
        string generationBinaryPath = "";
        DateTime generationStartedUtc = DateTime.MinValue;
        string lastGenerationRole = "";
        string lastGenerationFailure = "";
        readonly JavaScriptSerializer json = new JavaScriptSerializer();

        public C5Service()
        {
            ServiceName = ServiceNameConst;
            CanStop = true;
            CanShutdown = true;
            AutoLog = false;
        }

        protected override void OnStart(string[] args)
        {
            Directory.CreateDirectory(Root);
            CleanupRuntimeDebris();
            RotateWalIfNeeded();
            InitWalChain();
            InitializeGenerationIdentity();
            WriteGenerationState("CANDIDATE_EXCLUSIVE", "BOOTSTRAP");
            CleanupStaleSessionChildren();
            Wal("SERVICE_START", new Dictionary<string, object>{{"generation_id",generationId},{"generation_role","CANDIDATE_EXCLUSIVE"}});
            worker = new Thread(WorkerLoop);
            worker.IsBackground = true;
            worker.Name = "RAIOS-C5-ControlPlane";
            worker.Start();
        }

        protected override void OnStop()
        {
            WriteGenerationState("DRAINING", "SERVICE_STOP");
            Wal("SERVICE_STOP_REQUEST", new Dictionary<string, object>{{"generation_id",generationId}});
            stop.Set();
            KillUserLaneTree();
            KillDcrSupervisorTree();
            KillNativeTunnelTree();
            if (worker != null && worker.IsAlive) worker.Join(15000);
            WriteState("STOPPED", null);
            Wal("SERVICE_STOPPED", null);
        }

        protected override void OnShutdown()
        {
            OnStop();
            base.OnShutdown();
        }

        void WorkerLoop()
        {
            DateTime lastUserCheck = DateTime.MinValue;
            DateTime lastDcrCheck = DateTime.MinValue;
            DateTime lastTunnelCheck = DateTime.MinValue;
            DateTime lastHeadlessRepairCheck = DateTime.MinValue;
            DateTime lastBrokerCheck = DateTime.MinValue;
            DateTime lastHeartbeat = DateTime.MinValue;
            while (!stop.WaitOne(250))
            {
                try
                {
                    DateTime now = DateTime.UtcNow;
                    if ((now - lastDcrCheck).TotalSeconds >= 5)
                    {
                        EnsureDcrSupervisor();
                        lastDcrCheck = now;
                    }
                    if ((now - lastTunnelCheck).TotalSeconds >= 5)
                    {
                        EnsureNativeTunnel();
                        lastTunnelCheck = now;
                    }
                    if ((now - lastUserCheck).TotalSeconds >= 2)
                    {
                        EnsureUserLane();
                        lastUserCheck = now;
                    }
                    if ((now - lastHeadlessRepairCheck).TotalSeconds >= 5)
                    {
                        EnsureHeadlessNativeRecovery();
                        lastHeadlessRepairCheck = now;
                    }
                    if ((now - lastBrokerCheck).TotalMilliseconds >= 500)
                    {
                        RunBrokerIfPending();
                        lastBrokerCheck = now;
                    }
                    if ((now - lastHeartbeat).TotalSeconds >= 2)
                    {
                        WriteState("ONLINE", null);
                        UpdateGenerationPromotion();
                        lastHeartbeat = now;
                    }
                }
                catch (Exception ex)
                {
                    Wal("WORKER_ERROR", new Dictionary<string, object>{{"error", ex.GetType().Name + ":" + ex.Message}});
                    WriteState("DEGRADED", ex.GetType().Name);
                    WriteGenerationState("DEGRADED", ex.GetType().Name);
                    Thread.Sleep(1000);
                }
            }
        }


        bool KillProcessTreeVerified(int pid, int timeoutMs)
        {
            if (pid <= 4 || !IsPidAlive(pid)) return true;
            try
            {
                var psi = new ProcessStartInfo();
                psi.FileName = @"C:\Windows\System32\taskkill.exe";
                psi.Arguments = "/PID " + pid + " /T /F";
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                using (Process p = Process.Start(psi))
                {
                    if (p != null) p.WaitForExit(timeoutMs);
                }
            }
            catch {}
            if (IsPidAlive(pid))
            {
                try
                {
                    using (Process p = Process.GetProcessById(pid))
                    {
                        p.Kill();
                        p.WaitForExit(Math.Min(timeoutMs, 5000));
                    }
                }
                catch {}
            }
            return !IsPidAlive(pid);
        }

        bool IsDcrOwnedByCurrentService()
        {
            try
            {
                if (!File.Exists(DcrState)) return false;
                var st = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(DcrState));
                object pidObj, ownerObj, statusObj, authorityObj;
                if (!st.TryGetValue("supervisor_pid", out pidObj) ||
                    !st.TryGetValue("owner_pid", out ownerObj) ||
                    !st.TryGetValue("status", out statusObj) ||
                    !st.TryGetValue("authority", out authorityObj)) return false;
                return Convert.ToInt32(pidObj) == dcrSupervisorPid
                    && Convert.ToInt32(ownerObj) == Process.GetCurrentProcess().Id
                    && Convert.ToString(statusObj) == "ONLINE"
                    && Convert.ToString(authorityObj) == "RAIOS-C5";
            }
            catch { return false; }
        }

        void EnsureDcrSupervisor()
        {
            if (IsPidAlive(dcrSupervisorPid))
            {
                if (IsDcrOwnedByCurrentService()) return;
                try
                {
                    using (Process current = Process.GetProcessById(dcrSupervisorPid))
                    {
                        if ((DateTime.UtcNow - current.StartTime.ToUniversalTime()).TotalSeconds <= 120) return;
                    }
                }
                catch {}
            }
            if (DateTime.UtcNow < dcrRetryAfterUtc) return;

            try
            {
                if (File.Exists(DcrState))
                {
                    var st = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(DcrState));
                    object pidObj, ownerObj;
                    int existingPid = st.TryGetValue("supervisor_pid", out pidObj) ? Convert.ToInt32(pidObj) : 0;
                    int existingOwner = st.TryGetValue("owner_pid", out ownerObj) ? Convert.ToInt32(ownerObj) : 0;
                    if (existingPid > 4 && IsPidAlive(existingPid))
                    {
                        int currentServicePid = Process.GetCurrentProcess().Id;
                        if (existingOwner == currentServicePid)
                        {
                            if (dcrSupervisorPid != existingPid)
                            {
                                dcrSupervisorPid = existingPid;
                                Wal("DCR_OWNED_PID_REFRESH", new Dictionary<string, object>{{"pid",existingPid},{"owner_pid",existingOwner}});
                            }
                            return;
                        }
                        if (!KillProcessTreeVerified(existingPid, 8000))
                        {
                            Wal("DCR_STALE_OWNER_CLOSE_FAILED", new Dictionary<string, object>{{"pid",existingPid},{"owner_pid",existingOwner},{"expected_owner_pid",currentServicePid}});
                            dcrRetryAfterUtc = DateTime.UtcNow.AddSeconds(15);
                            dcrSupervisorPid = 0;
                            return;
                        }
                        Wal("DCR_STALE_OWNER_CLOSED", new Dictionary<string, object>{{"pid",existingPid},{"owner_pid",existingOwner},{"expected_owner_pid",currentServicePid}});
                    }
                }
            }
            catch (Exception ex)
            {
                Wal("DCR_STALE_OWNER_CHECK_FAILED", new Dictionary<string, object>{{"error",ex.GetType().Name + ":" + ex.Message}});
                dcrRetryAfterUtc = DateTime.UtcNow.AddSeconds(10);
                dcrSupervisorPid = 0;
                return;
            }

            dcrSupervisorPid = 0;
            if (!File.Exists(Python) || !File.Exists(DcrSupervisor))
                throw new FileNotFoundException("DCR_SUPERVISOR_PREREQUISITE_MISSING");

            var psi = new ProcessStartInfo();
            psi.FileName = Python;
            psi.Arguments = "\"" + DcrSupervisor + "\" --supervise";
            psi.WorkingDirectory = Path.GetDirectoryName(DcrSupervisor);
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.EnvironmentVariables["RAIOS_DCR_AUTHORITY"] = "RAIOS-C5";
            psi.EnvironmentVariables["RAIOS_DCR_OWNER_PID"] = Process.GetCurrentProcess().Id.ToString();
            var proc = Process.Start(psi);
            if (proc == null) throw new InvalidOperationException("DCR_SUPERVISOR_START_FAILED");
            dcrSupervisorPid = proc.Id;
            dcrRetryAfterUtc = DateTime.UtcNow.AddSeconds(30);
            Wal("DCR_SUPERVISOR_START", new Dictionary<string, object>{{"pid",proc.Id},{"mode","HEADLESS_SYSTEM"},{"owner_pid",Process.GetCurrentProcess().Id},{"retry_after_utc",dcrRetryAfterUtc.ToString("o")}});
        }

        bool IsLocalMcpReady()
        {
            try
            {
                var req = (System.Net.HttpWebRequest)System.Net.WebRequest.Create("http://127.0.0.1:8788/health");
                req.Method = "GET";
                req.Timeout = 2000;
                req.ReadWriteTimeout = 2000;
                req.Proxy = null;
                using (var resp = (System.Net.HttpWebResponse)req.GetResponse())
                using (var sr = new StreamReader(resp.GetResponseStream()))
                {
                    if ((int)resp.StatusCode != 200) return false;
                    string body = sr.ReadToEnd().Replace(" ", "").Replace("\r", "").Replace("\n", "");
                    return body.Contains("\"ok\":true")
                        && body.Contains("\"tool_count\":8")
                        && body.Contains("\"second_gateway\":false");
                }
            }
            catch { return false; }
        }

        bool IsNativeTunnelTransportAlive()
        {
            if (!File.Exists(TunnelHealthUrlFile)) return false;
            string baseUrl;
            try
            {
                baseUrl = File.ReadAllText(TunnelHealthUrlFile).Trim();
                if (!baseUrl.StartsWith("http://127.0.0.1:")) return false;
            }
            catch { return false; }

            try
            {
                var req = (System.Net.HttpWebRequest)System.Net.WebRequest.Create(baseUrl + "/metrics");
                req.Method = "GET";
                req.Timeout = 1500;
                req.ReadWriteTimeout = 1500;
                req.Proxy = null;
                using (var resp = (System.Net.HttpWebResponse)req.GetResponse())
                    if ((int)resp.StatusCode == 200) return true;
            }
            catch {}

            try
            {
                var req = (System.Net.HttpWebRequest)System.Net.WebRequest.Create(baseUrl + "/readyz");
                req.Method = "GET";
                req.Timeout = 1500;
                req.ReadWriteTimeout = 1500;
                req.Proxy = null;
                using (var resp = (System.Net.HttpWebResponse)req.GetResponse())
                    return ((int)resp.StatusCode == 200);
            }
            catch { return false; }
        }

        int ReadDeclaredNativeOwnerPid()
        {
            try
            {
                if (!File.Exists(TunnelOwnerState)) return 0;
                var st = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(TunnelOwnerState));
                object childObj, serviceObj, authorityObj;
                if (!st.TryGetValue("child_pid", out childObj) ||
                    !st.TryGetValue("service_pid", out serviceObj) ||
                    !st.TryGetValue("authority", out authorityObj)) return 0;
                int childPid = Convert.ToInt32(childObj);
                int servicePid = Convert.ToInt32(serviceObj);
                if (servicePid != Process.GetCurrentProcess().Id ||
                    Convert.ToString(authorityObj) != "RAIOS-C5-SCM" ||
                    !IsPidAlive(childPid)) return 0;
                try
                {
                    using (Process p = Process.GetProcessById(childPid))
                        if (!String.Equals(p.ProcessName, "tunnel-client", StringComparison.OrdinalIgnoreCase)) return 0;
                }
                catch { return 0; }
                return childPid;
            }
            catch { return 0; }
        }

        bool IsNativeOwnedByCurrentService()
        {
            int declared = ReadDeclaredNativeOwnerPid();
            return declared > 4 && declared == nativeTunnelPid;
        }

        bool IsNativeTunnelReady()
        {
            return IsNativeTunnelTransportAlive() && IsLocalMcpReady();
        }

        void ResetNativeTransportFailures()
        {
            nativeTransportFailureCount = 0;
            nativeTransportFailureSinceUtc = DateTime.MinValue;
        }

        bool NativeTransportFailureRequiresRestart(int pid)
        {
            DateTime now = DateTime.UtcNow;
            if (nativeTransportFailureCount == 0)
            {
                nativeTransportFailureSinceUtc = now;
                Wal("NATIVE_TUNNEL_TRANSPORT_DEGRADED_GRACE_START",
                    new Dictionary<string, object>{{"pid",pid},{"minimum_failures",6},{"minimum_seconds",30}});
            }
            nativeTransportFailureCount++;
            double elapsed = nativeTransportFailureSinceUtc == DateTime.MinValue
                ? 0 : (now - nativeTransportFailureSinceUtc).TotalSeconds;
            if (nativeTransportFailureCount < 6 || elapsed < 30) return false;
            Wal("NATIVE_TUNNEL_TRANSPORT_DEGRADED_GRACE_EXHAUSTED",
                new Dictionary<string, object>{{"pid",pid},{"failures",nativeTransportFailureCount},{"elapsed_seconds",elapsed}});
            return true;
        }

        int ScheduleNativeRetryBackoff(string reason)
        {
            nativeLaunchFailureCount = Math.Min(nativeLaunchFailureCount + 1, 5);
            int seconds = Math.Min(300, 15 * (1 << (nativeLaunchFailureCount - 1)));
            tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(seconds);
            Wal("NATIVE_TUNNEL_RETRY_BACKOFF",
                new Dictionary<string, object>{{"reason",reason},{"failure_count",nativeLaunchFailureCount},{"seconds",seconds},{"retry_after_utc",tunnelRetryAfterUtc.ToString("o")}});
            return seconds;
        }

        void ResetNativeRecoveryCounters()
        {
            ResetNativeTransportFailures();
            nativeLaunchFailureCount = 0;
        }

        void EnsureNativeTunnel()
        {
            var systemTunnels = new List<Process>();
            var userTunnels = new List<Process>();
            foreach (var existing in Process.GetProcessesByName("tunnel-client"))
            {
                try
                {
                    if (!String.Equals(existing.MainModule.FileName, TunnelClient, StringComparison.OrdinalIgnoreCase))
                    {
                        existing.Dispose();
                        continue;
                    }
                    if (existing.SessionId == 0) systemTunnels.Add(existing);
                    else userTunnels.Add(existing);
                }
                catch { try { existing.Dispose(); } catch {} }
            }

            if (userTunnels.Count > 0)
            {
                int failed = 0;
                foreach (var existing in userTunnels)
                {
                    if (!KillProcessTreeVerified(existing.Id, 5000)) failed++;
                    try { existing.Dispose(); } catch {}
                }
                if (failed > 0)
                {
                    Wal("NATIVE_TUNNEL_USER_DUPLICATE_CLOSE_FAILED", new Dictionary<string, object>{{"count",userTunnels.Count},{"failed",failed}});
                    tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(15);
                    return;
                }
                Wal("NATIVE_TUNNEL_USER_DUPLICATES_CLOSED", new Dictionary<string, object>{{"count",userTunnels.Count}});
            }

            if (systemTunnels.Count > 1)
            {
                int failed = 0;
                foreach (var existing in systemTunnels)
                {
                    if (!KillProcessTreeVerified(existing.Id, 5000)) failed++;
                    try { existing.Dispose(); } catch {}
                }
                nativeTunnelPid = 0;
                if (failed > 0)
                {
                    Wal("NATIVE_TUNNEL_DUPLICATE_CLOSE_FAILED", new Dictionary<string, object>{{"count",systemTunnels.Count},{"failed",failed}});
                    tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(15);
                    return;
                }
                Wal("NATIVE_TUNNEL_DUPLICATES_CLOSED", new Dictionary<string, object>{{"count",systemTunnels.Count}});
                tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(2);
                return;
            }

            int declaredNativePid = ReadDeclaredNativeOwnerPid();
            if (declaredNativePid > 4)
            {
                nativeTunnelPid = declaredNativePid;
                if (IsNativeTunnelTransportAlive())
                {
                    ResetNativeRecoveryCounters();
                    return;
                }
                try
                {
                    using (Process declared = Process.GetProcessById(declaredNativePid))
                        if ((DateTime.UtcNow - declared.StartTime.ToUniversalTime()).TotalSeconds <= 120) return;
                }
                catch {}
                if (!NativeTransportFailureRequiresRestart(declaredNativePid)) return;
                bool declaredClosed = KillProcessTreeVerified(declaredNativePid, 5000);
                nativeTunnelPid = 0;
                ResetNativeTransportFailures();
                Wal(declaredClosed ? "NATIVE_TUNNEL_TRANSPORT_UNHEALTHY_CLOSED" : "NATIVE_TUNNEL_TRANSPORT_UNHEALTHY_CLOSE_FAILED",
                    new Dictionary<string, object>{{"pid",declaredNativePid}});
                if (declaredClosed) ScheduleNativeRetryBackoff("DECLARED_TRANSPORT_UNHEALTHY");
                else tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(30);
                return;
            }

            if (systemTunnels.Count == 1)
            {
                var existing = systemTunnels[0];
                if (nativeTunnelPid != existing.Id)
                {
                    bool launchedByCurrentGeneration = nativeTunnelLauncherStartedUtc != DateTime.MinValue
                        && (DateTime.UtcNow - nativeTunnelLauncherStartedUtc).TotalSeconds <= 70;
                    if (!launchedByCurrentGeneration)
                    {
                        int stalePid = existing.Id;
                        bool closed = KillProcessTreeVerified(stalePid, 5000);
                        try { existing.Dispose(); } catch {}
                        nativeTunnelPid = 0;
                        if (!closed)
                        {
                            Wal("NATIVE_TUNNEL_STALE_CLOSE_FAILED", new Dictionary<string, object>{{"pid",stalePid}});
                            tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(15);
                            return;
                        }
                        Wal("NATIVE_TUNNEL_STALE_CLOSED", new Dictionary<string, object>{{"pid",stalePid}});
                        tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(2);
                        return;
                    }
                    nativeTunnelPid = existing.Id;
                    Wal("NATIVE_TUNNEL_OWNER_ESTABLISHED", new Dictionary<string, object>{{"pid",existing.Id},{"mode","SCM_SESSION0"},{"owner_pid",Process.GetCurrentProcess().Id}});
                }

                // Preserve a healthy transport while the MCP backend repairs.
                // Backend readiness gates Native RAIOS availability, not tunnel
                // process survival.
                if (IsNativeTunnelTransportAlive())
                {
                    ResetNativeRecoveryCounters();
                    return;
                }

                bool startupGrace = false;
                try { startupGrace = (DateTime.UtcNow - existing.StartTime.ToUniversalTime()).TotalSeconds <= 120; }
                catch {}
                if (startupGrace) return;

                int unhealthyPid = existing.Id;
                if (!NativeTransportFailureRequiresRestart(unhealthyPid)) return;
                bool killed = KillProcessTreeVerified(unhealthyPid, 5000);
                try { existing.Dispose(); } catch {}
                nativeTunnelPid = 0;
                ResetNativeTransportFailures();
                if (!killed)
                {
                    Wal("NATIVE_TUNNEL_UNHEALTHY_CLOSE_FAILED", new Dictionary<string, object>{{"pid",unhealthyPid}});
                    tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(30);
                    return;
                }
                Wal("NATIVE_TUNNEL_UNHEALTHY_CLOSED", new Dictionary<string, object>{{"pid",unhealthyPid}});
                ScheduleNativeRetryBackoff("TRANSPORT_UNHEALTHY");
                return;
            }

            nativeTunnelPid = 0;

            bool launcherAlive = false;
            if (nativeTunnelLauncherPid > 4)
            {
                try
                {
                    using (var launcher = Process.GetProcessById(nativeTunnelLauncherPid))
                    {
                        var started = launcher.StartTime.ToUniversalTime();
                        launcherAlive = !launcher.HasExited
                            && String.Equals(launcher.ProcessName, "powershell", StringComparison.OrdinalIgnoreCase)
                            && Math.Abs((started - nativeTunnelLauncherStartedUtc).TotalSeconds) <= 2;
                        if (launcherAlive && (DateTime.UtcNow - nativeTunnelLauncherStartedUtc).TotalSeconds > 120)
                        {
                            int timedOutPid = nativeTunnelLauncherPid;
                            bool closed = KillProcessTreeVerified(timedOutPid, 5000);
                            Wal(closed ? "NATIVE_TUNNEL_LAUNCHER_TIMEOUT_CLOSED" : "NATIVE_TUNNEL_LAUNCHER_TIMEOUT_CLOSE_FAILED",
                                new Dictionary<string, object>{{"pid",timedOutPid}});
                            if (closed) ScheduleNativeRetryBackoff("LAUNCHER_TIMEOUT");
                            else tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(30);
                            launcherAlive = false;
                        }
                    }
                }
                catch { launcherAlive = false; }
            }
            if (launcherAlive) return;
            nativeTunnelLauncherPid = 0;
            nativeTunnelLauncherStartedUtc = DateTime.MinValue;

            if (DateTime.UtcNow < tunnelRetryAfterUtc) return;
            if (!File.Exists(TunnelClient))
                throw new FileNotFoundException("NATIVE_TUNNEL_CLIENT_MISSING");
            if (!File.Exists(TunnelLauncher))
                throw new FileNotFoundException("NATIVE_TUNNEL_LAUNCHER_MISSING");

            var psi = new ProcessStartInfo();
            psi.FileName = PowerShell;
            psi.Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + TunnelLauncher + "\"";
            psi.WorkingDirectory = Path.GetDirectoryName(TunnelLauncher);
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.EnvironmentVariables["HOME"] = StableUserProfile;
            psi.EnvironmentVariables["USERPROFILE"] = StableUserProfile;
            psi.EnvironmentVariables["USERNAME"] = "Ghanam";
            psi.EnvironmentVariables["HOMEDRIVE"] = "C:";
            psi.EnvironmentVariables["HOMEPATH"] = @"\Users\Ghanam";
            psi.EnvironmentVariables["APPDATA"] = Path.Combine(StableUserProfile, @"AppData\Roaming");
            psi.EnvironmentVariables["LOCALAPPDATA"] = Path.Combine(StableUserProfile, @"AppData\Local");
            psi.EnvironmentVariables["TEMP"] = Path.Combine(StableUserProfile, @"AppData\Local\Temp");
            psi.EnvironmentVariables["TMP"] = Path.Combine(StableUserProfile, @"AppData\Local\Temp");
            psi.EnvironmentVariables["RAIOS_NATIVE_TUNNEL_AUTHORITY"] = "RAIOS-C5-SCM";
            psi.EnvironmentVariables["RAIOS_NATIVE_TUNNEL_OWNER_PID"] = Process.GetCurrentProcess().Id.ToString();
            var proc = Process.Start(psi);
            if (proc == null) throw new InvalidOperationException("NATIVE_TUNNEL_START_FAILED");
            nativeTunnelLauncherPid = proc.Id;
            try { nativeTunnelLauncherStartedUtc = proc.StartTime.ToUniversalTime(); }
            catch { nativeTunnelLauncherStartedUtc = DateTime.UtcNow; }
            tunnelRetryAfterUtc = DateTime.UtcNow.AddSeconds(5);
            Wal("NATIVE_TUNNEL_LAUNCHER_START", new Dictionary<string, object>{{"pid",proc.Id},{"mode","HEADLESS_SYSTEM_SINGLETON"},{"owner_pid",Process.GetCurrentProcess().Id},{"retry_after_utc",tunnelRetryAfterUtc.ToString("o")}});
        }

        void KillDcrSupervisorTree()
        {
            int pid = dcrSupervisorPid;
            dcrSupervisorPid = 0;
            if (pid <= 4) return;
            if (!KillProcessTreeVerified(pid, 8000))
                Wal("DCR_OWNED_TREE_CLOSE_FAILED", new Dictionary<string, object>{{"pid",pid}});
        }

        void KillNativeTunnelTree()
        {
            int[] pids = { nativeTunnelPid, nativeTunnelLauncherPid };
            nativeTunnelPid = 0;
            nativeTunnelLauncherPid = 0;
            nativeTunnelLauncherStartedUtc = DateTime.MinValue;
            foreach (int pid in pids)
            {
                if (pid <= 4) continue;
                if (!KillProcessTreeVerified(pid, 8000))
                    Wal("NATIVE_OWNED_TREE_CLOSE_FAILED", new Dictionary<string, object>{{"pid",pid}});
            }
        }

        void EnsureUserLane()
        {
            if (DateTime.UtcNow < userLaneRetryAfterUtc) return;
            uint session = WTSGetActiveConsoleSessionId();
            if (session == 0xFFFFFFFF)
            {
                if (userLanePid != 0) KillUserLaneTree();
                userLaneSession = 0xFFFFFFFF;
                userLaneRetryAfterUtc = DateTime.UtcNow.AddSeconds(15);
                WriteState("WAITING_FOR_USER_SESSION", null);
                return;
            }

            bool alive = IsPidAlive(userLanePid);
            if (alive && userLaneSession == session) return;

            KillUserLaneTree();
            try
            {
                CreateKillOnCloseJob();
                int pid = LaunchAsInteractiveUser(session);
                userLanePid = pid;
                userLaneSession = session;
                userLaneRetryAfterUtc = DateTime.MinValue;
                Wal("USER_LANE_START", new Dictionary<string, object>{{"pid",pid},{"session_id",session}});
            }
            catch (System.ComponentModel.Win32Exception ex)
            {
                KillUserLaneTree();
                userLanePid = 0;
                userLaneSession = 0xFFFFFFFF;
                userLaneRetryAfterUtc = DateTime.UtcNow.AddSeconds(30);
                Wal("USER_LANE_DEFERRED", new Dictionary<string, object>{{"error",ex.Message},{"retry_after_utc",userLaneRetryAfterUtc.ToString("o")}});
            }
        }

        void EnsureHeadlessNativeRecovery()
        {
            if (IsPidAlive(userLanePid)) return;
            if (IsPidAlive(headlessRepairPid))
            {
                if ((DateTime.UtcNow - headlessRepairStartedUtc).TotalSeconds <= 720) return;
                try { Process.GetProcessById(headlessRepairPid).Kill(); } catch {}
                Wal("HEADLESS_NATIVE_REPAIR_TIMEOUT", new Dictionary<string, object>{{"pid",headlessRepairPid}});
                headlessRepairPid = 0;
                headlessRepairRetryAfterUtc = DateTime.UtcNow.AddSeconds(30);
                return;
            }
            headlessRepairPid = 0;
            if (DateTime.UtcNow < headlessRepairRetryAfterUtc) return;
            if (!File.Exists(MaintainScript)) throw new FileNotFoundException("MAINTAIN_SCRIPT_MISSING");
            var psi = new ProcessStartInfo();
            psi.FileName = PowerShell;
            psi.Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + MaintainScript + "\" -Repo \"" + Repo + "\"";
            psi.WorkingDirectory = Repo;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.EnvironmentVariables["HOME"] = StableUserProfile;
            psi.EnvironmentVariables["USERPROFILE"] = StableUserProfile;
            psi.EnvironmentVariables["USERNAME"] = "Ghanam";
            psi.EnvironmentVariables["HOMEDRIVE"] = "C:";
            psi.EnvironmentVariables["HOMEPATH"] = @"\Users\Ghanam";
            psi.EnvironmentVariables["APPDATA"] = Path.Combine(StableUserProfile, @"AppData\Roaming");
            psi.EnvironmentVariables["LOCALAPPDATA"] = Path.Combine(StableUserProfile, @"AppData\Local");
            psi.EnvironmentVariables["TEMP"] = Path.Combine(StableUserProfile, @"AppData\Local\Temp");
            psi.EnvironmentVariables["TMP"] = Path.Combine(StableUserProfile, @"AppData\Local\Temp");
            psi.EnvironmentVariables["RAIOS_CANONICAL_REPO"] = Repo;
            var proc = Process.Start(psi);
            if (proc == null) throw new InvalidOperationException("HEADLESS_NATIVE_REPAIR_START_FAILED");
            headlessRepairPid = proc.Id;
            headlessRepairStartedUtc = DateTime.UtcNow;
            headlessRepairRetryAfterUtc = DateTime.UtcNow.AddSeconds(300);
            Wal("HEADLESS_NATIVE_REPAIR_START", new Dictionary<string, object>{{"pid",proc.Id},{"mode","SYSTEM_FALLBACK"},{"retry_after_utc",headlessRepairRetryAfterUtc.ToString("o")}});
        }

        void RunBrokerIfPending()
        {
            if (!File.Exists(BrokerRequest)) return;
            var psi = new ProcessStartInfo();
            psi.FileName = PowerShell;
            psi.Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + BrokerScript + "\"";
            psi.WorkingDirectory = Path.GetDirectoryName(BrokerScript);
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            using (Process p = Process.Start(psi))
            {
                if (!p.WaitForExit(45000))
                {
                    try { p.Kill(); } catch {}
                    Wal("BROKER_TIMEOUT", new Dictionary<string, object>{{"pid",p.Id}});
                }
                else
                {
                    Wal("BROKER_EXIT", new Dictionary<string, object>{{"pid",p.Id},{"exit_code",p.ExitCode}});
                }
            }
        }

        int LaunchAsInteractiveUser(uint sessionId)
        {
            IntPtr userToken = IntPtr.Zero;
            IntPtr primaryToken = IntPtr.Zero;
            IntPtr env = IntPtr.Zero;
            PROCESS_INFORMATION pi = new PROCESS_INFORMATION();
            try
            {
                if (!WTSQueryUserToken(sessionId, out userToken)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "WTSQueryUserToken");
                if (!DuplicateTokenEx(userToken, TOKEN_ALL_ACCESS, IntPtr.Zero, 2, 1, out primaryToken)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "DuplicateTokenEx");
                if (!CreateEnvironmentBlock(out env, primaryToken, false)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "CreateEnvironmentBlock");

                STARTUPINFO si = new STARTUPINFO();
                si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
                si.lpDesktop = @"winsta0\default";
                string args = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File \"" + UserLaneScript + "\"";
                StringBuilder cmd = new StringBuilder("\"" + PowerShell + "\" " + args);
                uint flags = CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW;
                bool ok = CreateProcessAsUserW(primaryToken, PowerShell, cmd, IntPtr.Zero, IntPtr.Zero, false, flags, env, Repo, ref si, out pi);
                if (!ok) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "CreateProcessAsUserW");
                if (job != IntPtr.Zero && !AssignProcessToJobObject(job, pi.hProcess))
                    throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "AssignProcessToJobObject");
                return (int)pi.dwProcessId;
            }
            finally
            {
                if (pi.hThread != IntPtr.Zero) CloseHandle(pi.hThread);
                if (pi.hProcess != IntPtr.Zero) CloseHandle(pi.hProcess);
                if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
                if (primaryToken != IntPtr.Zero) CloseHandle(primaryToken);
                if (userToken != IntPtr.Zero) CloseHandle(userToken);
            }
        }

        void CreateKillOnCloseJob()
        {
            if (job != IntPtr.Zero) CloseHandle(job);
            job = CreateJobObject(IntPtr.Zero, null);
            if (job == IntPtr.Zero) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "CreateJobObject");
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            int len = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
            IntPtr p = Marshal.AllocHGlobal(len);
            try
            {
                Marshal.StructureToPtr(info, p, false);
                if (!SetInformationJobObject(job, 9, p, (uint)len))
                    throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "SetInformationJobObject");
            }
            finally { Marshal.FreeHGlobal(p); }
        }

        void KillUserLaneTree()
        {
            if (job != IntPtr.Zero)
            {
                try { CloseHandle(job); } catch {}
                job = IntPtr.Zero;
            }
            userLanePid = 0;
            userLaneSession = 0xFFFFFFFF;
        }

        static bool IsPidAlive(int pid)
        {
            if (pid <= 4) return false;
            try { using (Process p = Process.GetProcessById(pid)) { return !p.HasExited; } }
            catch { return false; }
        }

        void InitializeGenerationIdentity()
        {
            generationStartedUtc = DateTime.UtcNow;
            try
            {
                using (Process p = Process.GetCurrentProcess())
                {
                    try { generationStartedUtc = p.StartTime.ToUniversalTime(); } catch {}
                    try { generationBinaryPath = p.MainModule.FileName; } catch { generationBinaryPath = ""; }
                }
            }
            catch {}
            if (String.IsNullOrWhiteSpace(generationBinaryPath))
                generationBinaryPath = Path.Combine(Root, "RAIOS-C5-Service.exe");
            try
            {
                using (SHA256 sha = SHA256.Create())
                using (FileStream fs = new FileStream(generationBinaryPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                    generationBinaryHash = BitConverter.ToString(sha.ComputeHash(fs)).Replace("-", "").ToLowerInvariant();
            }
            catch { generationBinaryHash = "UNKNOWN"; }
            generationId = generationBinaryHash + "::" + generationStartedUtc.ToString("o");
        }

        void UpdateGenerationPromotion()
        {
            bool dcrOwned = IsPidAlive(dcrSupervisorPid) && IsDcrOwnedByCurrentService();
            bool nativeReady = IsNativeTunnelReady();
            bool nativeOwned = nativeReady && IsNativeOwnedByCurrentService();
            bool mcpReady = IsLocalMcpReady();

            if (dcrOwned && nativeOwned && mcpReady)
            {
                WriteGenerationState("LEADER", null);
                return;
            }

            var missing = new List<string>();
            if (!dcrOwned) missing.Add("DCR");
            if (!nativeOwned) missing.Add("NATIVE");
            if (!mcpReady) missing.Add("MCP");
            WriteGenerationState("CANDIDATE_EXCLUSIVE", String.Join("+", missing.ToArray()));
        }

        void WriteGenerationState(string role, string failure)
        {
            if (String.IsNullOrWhiteSpace(generationId)) InitializeGenerationIdentity();
            string normalizedFailure = failure ?? "";
            if (role == lastGenerationRole && normalizedFailure == lastGenerationFailure) return;

            var obj = new Dictionary<string, object>();
            obj["schema"] = "raios.runtime-generation.v3";
            obj["observed_at"] = DateTime.UtcNow.ToString("o");
            obj["generation_id"] = generationId;
            obj["role"] = role;
            obj["authority"] = "RAIOS-C5-SCM";
            obj["service_pid"] = Process.GetCurrentProcess().Id;
            obj["service_binary"] = generationBinaryPath;
            obj["binary_sha256"] = generationBinaryHash;
            obj["started_at"] = generationStartedUtc.ToString("o");
            obj["predecessor_policy"] = "FOLLOW_MIGRATE_DRAIN";
            obj["predecessor_authority_allowed"] = false;
            obj["native_raios_role"] = "PRIMARY_CHANNEL";
            obj["rdc_role"] = "REMOTE_CAPABILITY_PROVIDER";
            obj["scheduler_authority"] = false;
            obj["resource_law"] = "ALL_RAIOS_OWNED_OR_ACQUIRED_CAPABILITIES_SERVE_PRIMARY_NATIVE_RAIOS_CHANNEL";
            obj["dcr_supervisor_pid"] = dcrSupervisorPid > 4 ? (object)dcrSupervisorPid : null;
            obj["native_tunnel_pid"] = nativeTunnelPid > 4 ? (object)nativeTunnelPid : null;
            obj["mcp_ready"] = IsLocalMcpReady();
            obj["failure"] = String.IsNullOrWhiteSpace(failure) ? null : (object)failure;
            obj["acceptance"] = role == "LEADER" ? "PASS" : "PENDING";
            obj["ok"] = role == "LEADER";

            try
            {
                File.WriteAllText(GenerationStatePath, json.Serialize(obj), new UTF8Encoding(false));
                if (role == "LEADER" && lastGenerationRole != "LEADER")
                {
                    File.WriteAllText(GenerationReceiptPath, json.Serialize(obj), new UTF8Encoding(false));
                    Wal("GENERATION_PROMOTED", new Dictionary<string, object>{{"generation_id",generationId},{"service_pid",Process.GetCurrentProcess().Id}});
                }
                else if (lastGenerationRole != role || lastGenerationFailure != normalizedFailure)
                {
                    Wal("GENERATION_STATE", new Dictionary<string, object>{{"generation_id",generationId},{"role",role},{"failure",normalizedFailure}});
                }
                lastGenerationRole = role;
                lastGenerationFailure = normalizedFailure;
            }
            catch (Exception ex)
            {
                Wal("GENERATION_STATE_WRITE_FAILED", new Dictionary<string, object>{{"generation_id",generationId},{"error",ex.GetType().Name}});
            }
        }

        void WriteState(string status, string error)
        {
            bool nativeTransportAlive = IsNativeTunnelTransportAlive();
            bool nativeReady = IsNativeTunnelReady();
            bool dcrReady = IsPidAlive(dcrSupervisorPid);
            bool dcrOwned = dcrReady && IsDcrOwnedByCurrentService();
            bool nativeOwned = nativeReady && IsNativeOwnedByCurrentService();
            if (String.Equals(status, "ONLINE", StringComparison.OrdinalIgnoreCase) && (!nativeOwned || !dcrOwned))
                status = "DEGRADED";

            var obj = new Dictionary<string, object>();
            obj["schema"] = "raios.c5.control-plane.state.v3";
            obj["observed_at"] = DateTime.UtcNow.ToString("o");
            obj["status"] = status;
            obj["service_pid"] = Process.GetCurrentProcess().Id;
            obj["user_lane_pid"] = userLanePid == 0 ? (object)null : userLanePid;
            obj["user_lane_role"] = "INTERACTIVE_SESSION_ADAPTER";
            obj["user_lane_authority"] = false;
            obj["dcr_supervisor_pid"] = dcrSupervisorPid == 0 ? (object)null : dcrSupervisorPid;
            obj["dcr_ready"] = dcrReady;
            obj["dcr_owned_by_service"] = dcrOwned;
            obj["dcr_role"] = "REMOTE_CAPABILITY_PROVIDER";
            obj["dcr_authority"] = false;
            obj["native_tunnel_owner_pid"] = nativeTunnelPid == 0 ? (object)null : nativeTunnelPid;
            obj["native_tunnel_launcher_pid"] = nativeTunnelLauncherPid == 0 ? (object)null : nativeTunnelLauncherPid;
            obj["native_transport_alive"] = nativeTransportAlive;
            obj["native_tunnel_ready"] = nativeReady;
            obj["native_tunnel_owned_by_service"] = nativeOwned;
            obj["native_tunnel_authority"] = "RAIOS-C5-SCM";
            obj["native_channel_role"] = "SINGLE_EXTERNAL_RAIOS_CHANNEL";
            obj["active_session_id"] = userLaneSession == 0xFFFFFFFF ? (object)null : userLaneSession;
            obj["broker_pending"] = File.Exists(BrokerRequest);
            obj["authority"] = "RAIOS-C5";
            obj["control_authority"] = "RAIOS-C5-SCM";
            obj["single_control_authority"] = true;
            obj["scheduler_authority"] = false;
            obj["error"] = error;
            AtomicJson(StatePath, obj);
        }

        void AtomicJson(string path, Dictionary<string, object> obj)
        {
            string tmp = path + ".tmp-" + Guid.NewGuid().ToString("N");
            try
            {
                File.WriteAllText(tmp, json.Serialize(obj), new UTF8Encoding(false));
                if (File.Exists(path)) File.Replace(tmp, path, null); else File.Move(tmp, path);
            }
            finally
            {
                try { if (File.Exists(tmp)) File.Delete(tmp); } catch {}
            }
        }

        void KillProcessTreeBestEffort(int pid, string reason)
        {
            if (pid <= 4 || !IsPidAlive(pid)) return;
            bool closed = KillProcessTreeVerified(pid, 8000);
            Wal(closed ? "STALE_CHILD_CLOSED" : "STALE_CHILD_CLOSE_FAILED",
                new Dictionary<string, object>{{"pid",pid},{"reason",reason}});
        }

        void CleanupStaleSessionChildren()
        {
            try
            {
                string userStatePath = Path.Combine(Root, "user-lane-state.json");
                if (!File.Exists(userStatePath)) return;
                var state = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(userStatePath));
                object pidObj;
                if (state.TryGetValue("pid", out pidObj) && pidObj != null)
                    KillProcessTreeBestEffort(Convert.ToInt32(pidObj), "PREVIOUS_USER_LANE");
                object maintainObj;
                if (state.TryGetValue("maintain_pid", out maintainObj) && maintainObj != null)
                    KillProcessTreeBestEffort(Convert.ToInt32(maintainObj), "PREVIOUS_MAINTAIN_CHILD");
            }
            catch {}
        }

        void CleanupRuntimeDebris()
        {
            try
            {
                foreach (string f in Directory.GetFiles(Root, "state.json.tmp-*"))
                {
                    try
                    {
                        if ((DateTime.UtcNow - File.GetLastWriteTimeUtc(f)).TotalMinutes > 2) File.Delete(f);
                    }
                    catch {}
                }
            }
            catch {}
        }

        string ReadLastNonEmptyLine(string path)
        {
            try
            {
                if (!File.Exists(path)) return null;
                using (FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                {
                    long start = Math.Max(0, fs.Length - 65536);
                    fs.Seek(start, SeekOrigin.Begin);
                    using (StreamReader sr = new StreamReader(fs, Encoding.UTF8, true, 4096, false))
                    {
                        if (start > 0) sr.ReadLine();
                        string last = null, line;
                        while ((line = sr.ReadLine()) != null)
                            if (!String.IsNullOrWhiteSpace(line)) last = line;
                        return last;
                    }
                }
            }
            catch { return null; }
        }

        void RotateWalIfNeeded()
        {
            try
            {
                if (!File.Exists(WalPath) || new FileInfo(WalPath).Length < 8388608) return;
                for (int i = 3; i >= 1; i--)
                {
                    string target = WalPath + "." + i;
                    string source = i == 1 ? WalPath : WalPath + "." + (i - 1);
                    if (!File.Exists(source)) continue;
                    try { if (File.Exists(target)) File.Delete(target); } catch {}
                    try { File.Move(source, target); } catch {}
                }
            }
            catch {}
        }

        void InitWalChain()
        {
            try
            {
                string line = ReadLastNonEmptyLine(WalPath);
                if (String.IsNullOrWhiteSpace(line)) line = ReadLastNonEmptyLine(WalPath + ".1");
                if (String.IsNullOrWhiteSpace(line)) return;
                var d = json.Deserialize<Dictionary<string, object>>(line);
                object h;
                if (d.TryGetValue("event_hash", out h) && h != null) lastHash = Convert.ToString(h);
            }
            catch { lastHash = ""; }
        }

        void Wal(string kind, Dictionary<string, object> extra)
        {
            try
            {
                RotateWalIfNeeded();
                var e = new Dictionary<string, object>();
                e["schema"] = "raios.c5.control-plane.event.v1";
                e["ts"] = DateTime.UtcNow.ToString("o");
                e["kind"] = kind;
                e["service_pid"] = Process.GetCurrentProcess().Id;
                e["prev_hash"] = lastHash;
                if (extra != null) foreach (var kv in extra) e[kv.Key] = kv.Value;
                string baseJson = json.Serialize(e);
                using (SHA256 sha = SHA256.Create())
                {
                    lastHash = BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(baseJson))).Replace("-", "").ToLowerInvariant();
                }
                e["event_hash"] = lastHash;
                byte[] bytes = Encoding.UTF8.GetBytes(json.Serialize(e) + Environment.NewLine);
                using (FileStream fs = new FileStream(WalPath, FileMode.Append, FileAccess.Write, FileShare.Read))
                {
                    fs.Write(bytes, 0, bytes.Length);
                    fs.Flush(true);
                }
            }
            catch {}
        }

        public static int SelfTest()
        {
            Directory.CreateDirectory(Root);
            string[] required = { PowerShell, Python, UserLaneScript, BrokerScript, DcrSupervisor, TunnelClient, TunnelLauncher };
            foreach (string p in required) if (!File.Exists(p)) { Console.WriteLine("SELFTEST_FAIL_MISSING=" + p); return 2; }
            Console.WriteLine("SELFTEST=PASS");
            Console.WriteLine("ACTIVE_SESSION=" + WTSGetActiveConsoleSessionId());
            Console.WriteLine("ROOT=" + Root);
            return 0;
        }

        public static void Main(string[] args)
        {
            if (args.Length > 0 && args[0] == "--selftest") { Environment.Exit(SelfTest()); return; }
            ServiceBase.Run(new C5Service());
        }

        const uint TOKEN_ALL_ACCESS = 0xF01FF;
        const uint CREATE_UNICODE_ENVIRONMENT = 0x00000400;
        const uint CREATE_NO_WINDOW = 0x08000000;
        const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;

        [DllImport("kernel32.dll")] static extern uint WTSGetActiveConsoleSessionId();
        [DllImport("Wtsapi32.dll", SetLastError=true)] static extern bool WTSQueryUserToken(uint SessionId, out IntPtr phToken);
        [DllImport("advapi32.dll", SetLastError=true)] static extern bool DuplicateTokenEx(IntPtr ExistingTokenHandle, uint dwDesiredAccess, IntPtr lpTokenAttributes, int ImpersonationLevel, int TokenType, out IntPtr DuplicateTokenHandle);
        [DllImport("userenv.dll", SetLastError=true)] static extern bool CreateEnvironmentBlock(out IntPtr lpEnvironment, IntPtr hToken, bool bInherit);
        [DllImport("userenv.dll", SetLastError=true)] static extern bool DestroyEnvironmentBlock(IntPtr lpEnvironment);
        [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateProcessAsUserW(IntPtr hToken, string lpApplicationName, StringBuilder lpCommandLine, IntPtr lpProcessAttributes, IntPtr lpThreadAttributes, bool bInheritHandles, uint dwCreationFlags, IntPtr lpEnvironment, string lpCurrentDirectory, ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);
        [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);
        [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr hJob, int JobObjectInfoClass, IntPtr lpJobObjectInfo, uint cbJobObjectInfoLength);
        [DllImport("kernel32.dll", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);
        [DllImport("kernel32.dll", SetLastError=true)] static extern bool CloseHandle(IntPtr hObject);

        [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
        struct STARTUPINFO
        {
            public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
            public uint dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
            public short wShowWindow, cbReserved2; public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
        }
        [StructLayout(LayoutKind.Sequential)]
        struct PROCESS_INFORMATION { public IntPtr hProcess, hThread; public uint dwProcessId, dwThreadId; }
        [StructLayout(LayoutKind.Sequential)]
        struct JOBOBJECT_BASIC_LIMIT_INFORMATION
        {
            public long PerProcessUserTimeLimit, PerJobUserTimeLimit; public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize; public uint ActiveProcessLimit;
            public UIntPtr Affinity; public uint PriorityClass, SchedulingClass;
        }
        [StructLayout(LayoutKind.Sequential)]
        struct IO_COUNTERS
        {
            public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount;
        }
        [StructLayout(LayoutKind.Sequential)]
        struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        {
            public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation; public IO_COUNTERS IoInfo;
            public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
        }
    }
}