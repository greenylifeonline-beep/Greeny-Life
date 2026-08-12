
import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = {
  vus: __ENV.K6_VUS || 10,
  duration: __ENV.K6_DURATION || '10s',
  thresholds: { http_req_duration: ['p(95)<500'], http_req_failed: ['rate<0.05'] },
};
export default function () {
  const res = http.get(__ENV.TARGET_URL || 'http://localhost:3000/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
