import { PrismaClient } from "@prisma/client";
import { hashPassword, roles, type AppRole } from "../lib/auth";

async function main() {
  const [emailArg, nameArg, roleArg] = process.argv.slice(2);
  const password = process.env.INIT_ADMIN_PASSWORD;
  const email = emailArg?.trim().toLowerCase(); const name = nameArg?.trim(); const role = (roleArg?.trim().toUpperCase() || "ADMIN") as AppRole;
  if (!email || !name || !password) throw new Error("Usage: set INIT_ADMIN_PASSWORD then run tsx scripts/provision-admin.ts email name [role].");
  if (!roles.includes(role)) throw new Error(`Role must be one of: ${roles.join(", ")}`);
  const prisma = new PrismaClient();
  try { await prisma.user.upsert({ where: { email }, update: { name, role, passwordHash: hashPassword(password) }, create: { email, name, role, passwordHash: hashPassword(password) } }); console.log(`Provisioned ${role} user ${email}.`); }
  finally { await prisma.$disconnect(); }
}
main().catch((error) => { console.error(error.message); process.exitCode = 1; });