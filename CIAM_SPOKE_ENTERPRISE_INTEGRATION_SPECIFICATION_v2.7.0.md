# ข้อกำหนดมาตรฐานกลาง: การเชื่อมต่อระบบลูกกับ Central IAM ผ่าน System Settings & Transaction Logs
**Standard Specification:** Enterprise Central IAM Integration for Spoke Applications  
**Current Version:** 2.7.0 (Mode C Two-Way Directory Reconciliation, Immediate Sync Button & RFC 9700 SSO)  
**Effective Date:** 8 ตุลาคม 2026 (08/10/2026)  
**Organization:** บริษัท วินโดว์ เอเชีย จำกัด (มหาชน) (Window Asia Public Company Limited)  
**Target Systems:** IRM, QMS, QOL (QT-Online), SAP B1 Service, MTPulse, ระบบงาน On-Premise ในโรงงาน และระบบงานทั้งหมดที่จะพัฒนาขึ้นใหม่  
**Compliance:** ISO 27001 / OpenID Connect (OIDC) / OAuth 2.0 with PKCE (RFC 7636) / OAuth 2.0 Security BCP (RFC 9700)

---

## 0. ประวัติการแก้ไขเอกสารและบันทึกการเปลี่ยนแปลง (Document Revision History & Changelog)

ตารางบันทึกประวัติการปรับปรุงข้อกำหนดมาตรฐาน เพื่อให้ทีมพัฒนาทุกระบบ (Spoke Teams) สามารถตรวจสอบย้อนกลับและทราบความแตกต่างของข้อกำหนดในแต่ละเวอร์ชันตามมาตรฐาน ISO 27001:

| เวอร์ชัน (Version) | วันที่มีผล (Date) | สถานะ (Status) | สรุปรายการปรับปรุงจากเวอร์ชันก่อนหน้า (Change Summary & Key Differences) |
| :---: | :---: | :---: | :--- |
| **v2.7.0** | 08/10/2026 | **Current Active** | • **Mode C Two-Way Directory Reconciliation & Auto-Provisioning (หมวด D.2, D.4):** กำหนดให้การเชื่อมต่อ Mode C เป็นแบบ Two-Way Reconciliation อย่างแท้จริง โดยเมื่อ Spoke ส่ง Heartbeat / Full Sync ขึ้นมา CIAM จะเปรียบเทียบกับบัญชีที่ได้รับสิทธิ์ใน CIAM (`AppAccountMapping`). หาก CIAM มีบัญชีใหม่ที่ Spoke ยังไม่มี CIAM จะส่ง `assigned_accounts` และคำสั่ง `PROVISION_USER` กลับไปเพื่อให้ Spoke สร้างบัญชีใน Local Database ทันที (Role เริ่มต้นตาม `ciam_auto_provision_group`, `is_active: true`) และส่งคำสั่ง `DISABLE_USER` หากถูกระงับสิทธิ์ ทำให้จำนวนและสถานะตรงกัน 100% โดยไม่ต้องรอ User ล็อกอิน<br/>• **Mandatory Spoke Mode C Immediate Sync Button (หมวด D.4, 5.1):** ข้อบังคับสำหรับ Spoke Mode C ต้องมีปุ่ม **`[ ⚡ ซิงก์บัญชีผู้ใช้กับ CIAM ทันที ]` (Immediate Account Sync)** บนหน้าจอ System Setting เพื่อให้ Admin สั่งแลกเปลี่ยนข้อมูลและปรับยอดจำนวนบัญชีรวมถึงสถานะ Active/Inactive ให้ตรงกันได้แบบเรียลไทม์โดยไม่ต้องรอรอบเวลา 120 วินาที<br/>• **RFC 9700 Seamless SSO Bounce Standard (หมวด B.3):** กำหนดมาตรฐานการเปิดใช้งานจาก Employee Portal ผ่าน SSO Start Endpoint (`/auth/start`) เพื่อให้ Spoke ผูก Client State & PKCE กับเบราว์เซอร์ได้สมบูรณ์ 100% ตามคำแนะนำ RFC 9700 |
| **v2.6.0** | 07/10/2026 | Superseded | • **RFC 9700 Seamless SSO Bounce Standard (หมวด B.3):** กำหนดมาตรฐานการเปิดใช้งานจาก Employee Portal ผ่าน SSO Start Endpoint (`/auth/start`)<br/>• **Architecture Equivalence Principles (หมวด 1.4):** บรรจุหลักการยอมรับสถาปัตยกรรมภายในที่เทียบเท่า<br/>• **Mode C Full Sync Trigger Protocol (หมวด D.2):** เพิ่มคำสั่ง `REQUEST_FULL_SYNC` ใน Heartbeat Command Queue |
| **v2.5.0** | 07/10/2026 | Superseded | • **Dual-Mode SSO & Portal Launch Support:** เพิ่มข้อกำหนดการรองรับการเปิดจาก Portal และข้อกำหนดความปลอดภัยของ Callback |
| **v2.4.0** | 05/10/2026 | Superseded | • **Mode C Outbound Agent Specification:** เพิ่มมาตรฐาน Reverse Heartbeat & Command Pull (`POST /api/v1/agent/heartbeat`) สำหรับระบบ On-Premise ที่ไม่มี Inbound Public Port |
| **v2.3.0** | 03/10/2026 | Superseded | • **Zero-Trust Network Policy:** กำหนดมาตรฐานการจำกัดการเข้าถึงผ่าน VPN (`VPN_ONLY`, `HIDE`, `LOCK_WITH_BANNER`) พร้อมระบุ Corporate Subnets |
| **v2.2.0** | 01/10/2026 | Superseded | • **Local Account Management:** รองรับบัญชีที่ไม่ใช่ Active Directory ผ่านฟิลด์ `use_ad_auth: false` |
| **v2.1.0** | 28/09/2026 | Superseded | • **Break-Glass Emergency Switch:** กำหนดมาตรฐานโหมดปลดระบบฉุกเฉินระดับ ISO 27001 ให้สลับไปใช้ Direct AD Gateway หรือ Local Credential |
| **v2.0.0** | 25/09/2026 | Superseded | • **OIDC PKCE S256 & Asymmetric RS256 Verification:** ยกระดับความปลอดภัยการยืนยันตัวตนด้วย Asymmetric RS256 Public Key ผ่าน JWKS |
| **v1.0.0** | 15/09/2026 | Superseded | • ร่างข้อกำหนดการเชื่อมต่อระบบลูกเวอร์ชันแรก (REST M2M API, Two-Way Directory Sync และ System Settings) |

---

## 1. บทนำและหลักการออกแบบ (Architecture Principles)

เอกสารฉบับนี้กำหนดมาตรฐานการเชื่อมต่อระบบสารสนเทศภายในเครือบริษัท วินโดว์ เอเชีย จำกัด (มหาชน) ทั้งหมด เข้ากับระบบพิสูจน์ตัวตนกลาง **Window Asia Central IAM** เพื่อให้ทุกระบบย่อย (Spoke Applications) มีโครงสร้าง API, สถาปัตยกรรมการจัดเก็บการตั้งค่า และรูปแบบการบันทึก Audit Log เป็น **Template มาตรฐานเดียวกัน 100%**

### 1.1 รูปแบบสภาพแวดล้อมระบบและการเชื่อมต่อเครือข่าย (Deployment Topologies)
Central IAM รองรับสภาพแวดล้อมระบบลูกทั้ง Cloud และ On-Premise โดยแบ่งการเชื่อมต่อเป็น **3 รูปแบบหลัก** ที่ Developer ต้องเลือกใช้ให้ตรงกับระบบของตนเอง:

| มิติการพิจารณา | 🌐 Mode A: Cloud Two-Way (เช่น IRM, QMS) | 🏢 Mode B: On-Premise SSO-Only (ระบบทั่วไป) | 🚀 Mode C: On-Prem Outbound Agent (แนะนำสำหรับ On-Prem) |
| :--- | :--- | :--- | :--- |
| **ตำแหน่งติดตั้ง** | Hostinger, AWS, GCP หรือ Public Cloud | สำนักงานใหญ่ / ในโรงงาน / Local Private Network | สำนักงานใหญ่ / เครื่องในโรงงาน / Local Private Network |
| **การเข้าถึงจากภายนอก** | มี Public Domain / IP เข้าถึงได้จากอินเทอร์เน็ต | **ไม่มี Inbound Tunnel จากภายนอก** (Private IP/Local) | **ไม่มี Inbound Tunnel จากภายนอก** (Private IP/Local) |
| **พอร์ต Inbound ขาเข้า** | ต้องเปิด Inbound HTTPS (Port 443) ให้ CIAM ยิงเข้ามาได้ | **❌ ไม่ต้องเปิด Inbound Port ใดๆ จากภายนอก** | **❌ ไม่ต้องเปิด Inbound Port ใดๆ จากภายนอก** |
| **พอร์ต Outbound ขาออก** | HTTPS (Port 443) ออกอินเทอร์เน็ต | HTTPS (Port 443) ออกอินเทอร์เน็ตเพื่อแลก Token | HTTPS (Port 443) ออกอินเทอร์เน็ตเพื่อแลก Token และยิง Heartbeat |
| **การจัดการบัญชีผู้ใช้** | CIAM กวาด Directory Sync และสั่ง 1-Click Offboard ตรง | Just-In-Time (JIT) Provisioning เมื่อ User ล็อกอินครั้งแรก | **Two-Way Reconciliation (CIAM ส่งบัญชีที่เพิ่มขึ้นไปให้ Spoke สร้างทันที + กวาด Sync + 1-Click Offboard)** |
| **ตรวจสถานะ Online/Offline** | CIAM ยิง Ping Inbound ตรง | ระบบมองเป็น Client Mode (พร้อมรับ SSO เสมอ) | **มี Heartbeat แท้จริง** (ถ้าไม่ส่งตามเวลาระบบจะปรับเป็น Offline) |
| **ความซับซ้อนฝั่ง Dev** | ทำ Endpoint กลุ่ม A, B, C | ทำ Endpoint กลุ่ม A, B (ไม่ต้องเขียน Background Service) | ทำกลุ่ม A, B + รันสคริปต์ **Agent เล็กๆ ยิง Heartbeat (กลุ่ม D)** + ปุ่ม Sync ทันที |
| **นโยบายเครือข่ายบน CIAM** | `network_policy: ANYWHERE` | `network_policy: VPN_ONLY` | `network_policy: VPN_ONLY` |

### 1.2 โหมดการเชื่อมต่อของระบบลูก (Spoke Integration Modes)
1. **Mode A: Full Two-Way Integration (SSO + Governance Webhooks):**  
   - สำหรับระบบที่มี Public Domain หรือเชื่อมต่อผ่าน Site-to-Site Tunnel ที่ Cloud ยิงเข้ามาได้  
   - พัฒนาครบทั้ง **Group A (Settings)**, **Group B (SSO Flow)**, และ **Group C (Directory & Status Inbound Webhook)**  
   - ข้อดี: CIAM สามารถตรวจเช็ค Health แบบ Inbound, กวาด Reconciliation บัญชีผีเวลา 04:00 น., และสั่ง 1-Click Deprovisioning ระงับสิทธิ์ทันทีเมื่อพนักงานลาออก
2. **Mode B: SSO-Only Client Mode (สำหรับ Isolated On-Premise แบบเรียบง่าย):**  
   - สำหรับระบบ On-Premise ที่ไม่มี Inbound Tunnel และ**ไม่ต้องการรัน Background Worker ใดๆ**  
   - พัฒนาเฉพาะ **Group B (SSO Flow - OIDC/PKCE)** และ **Group A (Settings)**  
   - **ไม่ต้องเปิด Group C (Inbound API)** ให้กับ CIAM  
   - การยืนยันตัวตนทำงานได้ 100% ผ่าน Client-side Browser Redirect และใช้ Just-In-Time (JIT) Provisioning
3. **Mode C: Outbound Agent Mode (Reverse Heartbeat & Command Queue — แนะนำสำหรับ On-Premise สำคัญ เช่น MTPulse, WMS, ERP):**  
   - สำหรับระบบ On-Premise ที่ต้องการฟังก์ชันระดับ Enterprise ครบถ้วน (กวาดรายชื่อบัญชีขึ้น CIAM + สั่งระงับสิทธิ์ 1-Click Offboarding + ตรวจสอบสถานะ Live Online/Offline) **โดยไม่ต้องเปิดพอร์ต Inbound ใดๆ บน Firewall ออฟฟิศ**  
   - พัฒนา **Group A (Settings)**, **Group B (SSO Flow)** และรันสคริปต์ **Group D (Outbound Heartbeat Agent)**  
   - Spoke จะตั้งเวลา (Cronjob หรือ Background Task ทุก 120 วินาที) ยิง Outbound HTTPS 443 ไปรายงานตัวที่ `POST https://ciam.windowasia.com/api/v1/agent/heartbeat` และดึงคำสั่งระงับสิทธิ์กลับมาทำงานในเครื่องตนเองโดยอัตโนมัติ

### 1.3 นโยบายความปลอดภัยเครือข่าย Zero-Trust VPN Access Control
เมื่อระบบลูกได้รับการตั้งค่านโยบายเครือข่ายเป็น `VPN_ONLY` บน Central IAM:
* **การตรวจสอบ Client IP แบบเรียลไทม์:** เมื่อพนักงานเปิดหน้า Employee Portal (`/portal`) เซิร์ฟเวอร์ CIAM จะตรวจสอบ Egress Public IP ของพนักงาน
* **Restriction Behavior:**
  * **โหมด `HIDE` (แนะนำสำหรับ On-Prem):** การ์ดระบบนี้จะถูกซ่อนออกจาก Portal ทันทีหากพนักงานไม่ได้เชื่อมต่อ VPN (เพื่อป้องกันความสับสน)
  * **โหมด `LOCK_WITH_BANNER`:** การ์ดจะแสดงพร้อมไอคอน 🔒 และปุ่มเปิดระบบจะถูกปิดใช้งาน (Disabled) พร้อมข้อความแจ้งเตือน *"กรุณาเชื่อมต่อ VPN ก่อนเข้าใช้งาน"*
* **รายการวงเครือข่ายที่อนุญาต (Corporate VPN & Office CIDRs):**
  * `49.231.185.245/32` (Window Asia HQ Gateway WAN - Egress IP หลักเมื่อต่อ Full Tunnel OpenVPN)
  * `58.8.190.63/32` (สำนักงานสำรอง)
  * `10.8.0.0/24` (OpenVPN Client Subnet)
  * `192.168.0.0/16` (Office LAN Subnet)
  * `157.173.219.153` (Public IP VPS ของเซิร์ฟเวอร์ Central IAM)

### ❌ ข้อห้ามสำคัญ (Zero `.env` Dependency):
* **ห้าม Hardcode ค่าการเชื่อมต่อ Central IAM ลงในไฟล์ `.env` บน Production:**  
  การเปลี่ยน URL, หมุนเวียน Client Secret หรือสลับโหมด Break-Glass จะต้องทำได้ทันทีผ่านฐานข้อมูล/หน้าจอ System Setting **โดยไม่ต้อง SSH เข้าเซิร์ฟเวอร์ VPS, ไม่ต้องแก้ไฟล์ `.env`, และไม่ต้องสั่ง Rebuild หรือ Restart Docker Containers**
* **Dynamic Configuration:**  
  ระบบลูกสามารถอ่านค่าคอนฟิกจากตารางฐานข้อมูล `system_settings` ตรงต่อคำขอ หรือแคชไว้ในหน่วยความจำ/Redis โดยต้องอัปเดตทันทีเมื่อมีการแก้ไขค่า

### 1.4 หลักความยืดหยุ่นเชิงสถาปัตยกรรมภายในระบบลูก (Architecture Equivalence Principles)

เอกสารฉบับนี้กำหนดมาตรฐานในเชิง **สัญญาการเชื่อมต่อและความปลอดภัย (Contract & Security Outcome)** เป็นหลัก โค้ดตัวอย่างที่แนบในเอกสารเป็นแนวทางอ้างอิง (Reference Implementation) ระบบลูกแต่ละระบบ**ไม่จำเป็นต้องแก้ไขระบบเดิมให้เหมือนตัวอย่างทุกบรรทัด** หากระบบลูกมีสถาปัตยกรรมภายในที่บรรลุผลลัพธ์ความปลอดภัยเทียบเท่าหรือรัดกุมกว่าตามมาตรฐานสากล:

1. **การจัดเก็บ PKCE State & Verifier:**
   * ตัวอย่างเอกสารแสดงการใช้ `sessionStorage` ฝั่ง Frontend
   * *รูปแบบเทียบเท่าที่ยอมรับและสนับสนุน:* ระบบลูกสามารถสร้างและจัดเก็บ PKCE Verifier ไว้บน Backend เช่น ใน Encrypted Session Cookie (HttpOnly, SameSite=Lax), Server-side Session Cache หรือตารางในฐานข้อมูล ซึ่งเป็นรูปแบบที่มีความปลอดภัยสูง ป้องกัน XSS ได้ดียิ่งขึ้น
2. **การจัดการ Session หลังยืนยันตัวตนสำเร็จ:**
   * ตัวอย่างเอกสารแสดงการส่ง Access Token คืนให้ Frontend
   * *รูปแบบเทียบเท่าที่ยอมรับ:* ระบบลูกสามารถออก Session Cookie แบบ HttpOnly เพื่อควบคุมสิทธิ์การเข้าใช้งานภายในระบบของตนเอง โดยไม่ต้องส่งต่อ Token ให้ JavaScript ฝั่ง Frontend
3. **การจับคู่ตัวตนผู้ใช้งาน (Identity Resolution):**
   * ระบบลูกสามารถผูกบัญชีเข้ากับตัวตนหลักใน Central IAM ได้โดยใช้ Claim: `sub` (CIAM Master ID), `preferred_username` (AD Username) หรือ `email` ตามความเหมาะสมของโครงสร้างฐานข้อมูลระบบลูก
4. **ความถี่และการอ่านค่าการตั้งค่า:**
   * ระบบลูกสามารถอ่านค่าจากฐานข้อมูลในแต่ละ Request หรือทำ In-memory Caching ก็ได้ ตราบใดที่ยังคงหลักการ **Zero `.env` Dependency** (เปลี่ยนการเชื่อมต่อได้ทันทีโดยไม่ต้อง Rebuild หรือ Deploy ใหม่)

---

## 2. โครงสร้างฐานข้อมูลมาตรฐาน (Database Schema Standard)

ระบบลูกทุกระบบต้องมีตารางฐานข้อมูล 2 ตารางนี้ (หรือเทียบเท่า) เพื่อรองรับการตั้งค่าและการตรวจสอบย้อนกลับ:

### 2.1 ตาราง `system_settings` (Dynamic Runtime Configuration)

```sql
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NULL,
    description VARCHAR(250) NULL,
    category VARCHAR(50) DEFAULT 'general',
    data_type VARCHAR(20) DEFAULT 'string', -- 'string', 'boolean', 'integer', 'encrypted'
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_settings_category ON system_settings(category);
CREATE INDEX idx_system_settings_key ON system_settings(key);
```

#### ชุดข้อมูลมาตรฐานตั้งต้น (Seed Data) สำหรับหมวด `central_iam`:

| Key | Data Type | Default Value ตัวอย่าง (IRM) | คำอธิบาย |
| :--- | :---: | :--- | :--- |
| `ciam_base_url` | string | `https://ciam.windowasia.com` | URL หลักของ Central IAM Engine (ห้ามมี `/` ต่อท้าย) |
| `ciam_client_id` | string | `irm-spoke-client` | Client ID ที่ลงทะเบียนไว้ในหน้า Central IAM Portal |
| `ciam_client_secret` | encrypted | `sec_irm_oauth_secret_2026` | รหัสลับเฉพาะของระบบลูก (ห้ามส่งคืนค่าเต็มผ่าน GET API) |
| `ciam_sso_enabled` | boolean | `true` | สวิตช์หลักเปิด/ปิดการเข้าใช้งานด้วย Central IAM SSO |
| `ciam_break_glass_active` | boolean | `false` | โหมดปลดระบบฉุกเฉิน (สลับไปล็อกอินตรงด้วย AD Gateway) |
| `ciam_ad_gateway_url` | string | `http://172.18.0.1:3100` | URL เซิร์ฟเวอร์ AD Gateway ภายในองค์กร |
| `ciam_auto_provision_group`| string | `PU Staff` | ชื่อกลุ่มสิทธิ์เริ่มต้นสำหรับพนักงานใหม่ที่ล็อกอินผ่าน SSO ครั้งแรก |
| `ciam_session_ttl_minutes` | integer | `480` | อายุ Access Token ของระบบลูก (ค่าแนะนำ: 8 ชั่วโมง / 480 นาที) |

---

### 2.2 ตาราง `transaction_logs` (ISO 27001 Security Audit Trail)

```sql
CREATE TABLE transaction_logs (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,          -- 'ciam_sso', 'security_break_glass', 'system_setting'
    action VARCHAR(100) NOT NULL,           -- เช่น 'login_success', 'login_failed', 'toggle_break_glass'
    status VARCHAR(20) DEFAULT 'success',   -- 'success', 'failed', 'warning', 'info'
    message VARCHAR(500) NOT NULL,          -- ข้อความสรุปเหตุการณ์ภาษาไทยที่อ่านเข้าใจง่าย
    details TEXT NULL,                      -- บันทึก JSON String รายละเอียด เช่น IP, Claims, Error, Diff
    records_count INT DEFAULT 0,
    duration_ms INT DEFAULT 0,
    triggered_by VARCHAR(100) NOT NULL,     -- 'user:<username>', 'system:ciam', 'system:emergency_admin'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trans_logs_category ON transaction_logs(category);
CREATE INDEX idx_trans_logs_created_at ON transaction_logs(created_at DESC);
```

---

## 3. ช่องทาง API มาตรฐานที่ระบบลูกต้องพัฒนา (Required API Channels)

ระบบลูกต้องเปิดหรือใช้งาน Endpoint ตามโครงสร้างมาตรฐาน **4 กลุ่มหลัก** (ขึ้นอยู่กับ Mode ที่เลือกตามข้อ 1.1):
* **Mode A (Cloud Two-Way):** พัฒนา **Group A, Group B และ Group C** (มี Public IP/Tunnel ให้ CIAM ยิงเข้ามา)
* **Mode B (On-Prem SSO-Only):** พัฒนา **Group A และ Group B** (ไม่มี Inbound Port, ผู้ใช้เข้าผ่าน SSO)
* **Mode C (On-Prem Outbound Agent เช่น MTPulse):** พัฒนา **Group A, Group B และ Group D** (**❌ ไม่ต้องเปิด Group C ใดๆ ทั้งสิ้น** ให้ใช้สคริปต์ Agent หมวด D ยิงออกไปรายงานตัวและดึงคำสั่งแทน)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     SPOKE APPLICATION API CHANNELS                                     │
├──────────────────────────────┬──────────────────────────────────┬──────────────────┬───────────────────┤
│ Group A: Settings Channel    │ Group B: SSO Authentication Flow │ Group C: Inbound │ Group D: Outbound │
│ (สิทธิ์เฉพาะ Admin ของระบบ)   │ (ยืนยันตัวตนกับ AD ผ่าน CIAM)     │ Directory (Mode A)│ Agent (Mode C)    │
│ [ทุกระบบต้องมี]               │ [ทุกระบบต้องมี]                   │ [เฉพาะ Mode A]   │ [เฉพาะ Mode C]    │
├──────────────────────────────┼──────────────────────────────────┼──────────────────┼───────────────────┤
│ • GET  /api/settings/ciam-sso│ • GET  /api/auth/sso/config      │ • GET  accounts  │ • POST /api/v1/   │
│ • PUT  /api/settings/ciam-sso│ • POST /api/auth/sso/            │ • POST accounts  │   agent/heartbeat │
│ • POST /api/settings/ciam-sso│         authorize-url            │ • PATCH accounts │ (On-Prem ยิงขึ้นหา│
│        /test-connection      │ • POST /api/auth/sso/callback    │   /{user}/status │  CIAM ทุก 120s)   │
│                              │ • POST /api/auth/sso/            │ (CIAM ยิงตรงเข้า │ (ดึงคำสั่ง &      │
│                              │         break-glass-toggle       │  หา Spoke Server)│  Sync บัญชี)      │
└──────────────────────────────┴──────────────────────────────────┴──────────────────┴───────────────────┘
```

---

### หมวด A: System Settings Management Channel (สำหรับ Admin)

#### A.1 `GET /api/settings/ciam-sso` (ดึงค่าคอนฟิกปัจจุบัน)
* **การจำกัดสิทธิ์:** ต้องตรวจสอบ JWT ของผู้ดูแลระบบ (`require_admin` หรือสิทธิ์ดู System Settings)
* **เงื่อนไขความปลอดภัย:** ต้อง Mask รหัสลับ `ciam_client_secret` ให้แสดงเฉพาะ 4 ตัวท้าย เช่น `sec_****_2026`

**Response Example (200 OK):**
```json
{
  "status": "success",
  "settings": {
    "ciam_base_url": "https://ciam.windowasia.com",
    "ciam_client_id": "irm-spoke-client",
    "ciam_client_secret_masked": "sec_****_2026",
    "ciam_sso_enabled": true,
    "ciam_break_glass_active": false,
    "ciam_ad_gateway_url": "http://172.18.0.1:3100",
    "ciam_auto_provision_group": "PU Staff",
    "ciam_session_ttl_minutes": 480,
    "updated_at": "2026-09-11T07:15:30Z"
  }
}
```

---

#### A.2 `PUT /api/settings/ciam-sso` (แก้ไขค่าคอนฟิก Central IAM แบบ Real-Time)
* **การจำกัดสิทธิ์:** Administrator เท่านั้น
* **พฤติกรรมระบบ:**
  1. บันทึกค่าใหม่ลงตาราง `system_settings`
  2. หากฟิลด์ `ciam_client_secret` ส่งมาเป็นค่าว่าง หรือขึ้นต้นด้วย `sec_****` ให้คงค่าเดิมไว้ ไม่เขียนทับ
  3. ล้าง In-Memory Cache เพื่อให้ Service อ่านค่าใหม่ทันที
  4. บันทึก `transaction_logs` หมวด `system_setting` พร้อมระบุ username ผู้แก้ไข และรายการฟิลด์ที่เปลี่ยน

**Request Body:**
```json
{
  "ciam_base_url": "https://ciam.windowasia.com",
  "ciam_client_id": "irm-spoke-client",
  "ciam_client_secret": "sec_irm_oauth_new_secret_2026", // ใส่เฉพาะเมื่อต้องการเปลี่ยน
  "ciam_sso_enabled": true,
  "ciam_ad_gateway_url": "http://172.18.0.1:3100",
  "ciam_auto_provision_group": "PU Staff",
  "ciam_session_ttl_minutes": 480
}
```

---

#### A.3 `POST /api/settings/ciam-sso/test-connection` (ทดสอบการเชื่อมต่อจาก VPS)
* **วัตถุประสงค์:** ใช้ตรวจสอบว่าเซิร์ฟเวอร์ IRM บน VPS สามารถยิงออกไปหาเซิร์ฟเวอร์ Central IAM ได้จริงหรือไม่
* **การทำงาน:**
  1. ดึง `ciam_base_url` จาก `system_settings`
  2. ยิง HTTP GET ไปยัง `${ciam_base_url}/.well-known/openid-configuration` ด้วย Timeout 3 วินาที
  3. ตรวจสอบสถานะการเชื่อมต่อ และทดสอบดึง JWKS Public Keys
  4. ส่งผลสรุปสถานะ ค่า Latency (ms) และ Key ID (kid) ให้ Admin ทราบ

**Response Example (200 OK):**
```json
{
  "status": "connected",
  "latency_ms": 38,
  "ciam_issuer": "https://ciam.windowasia.com",
  "jwks_uri": "https://ciam.windowasia.com/.well-known/jwks.json",
  "keys_found": 1,
  "key_id": "ciam-key-2026-01",
  "message": "สามารถเชื่อมต่อไปยัง Window Asia Central IAM ได้อย่างสมบูรณ์"
}
```

---

### หมวด B: Single Sign-On Execution Channel (สำหรับพนักงานและระบบ)

#### B.1 `GET /api/auth/sso/config` (อ่านสถานะเพื่อนำไปแสดงผลบนหน้าจอ Login)
* **การจำกัดสิทธิ์:** Public (ไม่ต้องล็อกอิน)

**Response Example (200 OK):**
```json
{
  "sso_enabled": true,
  "break_glass_active": false,
  "ciam_base_url": "https://ciam.windowasia.com",
  "client_id": "irm-spoke-client",
  "login_button_label": "เข้าสู่ระบบด้วย Central IAM (SSO)",
  "fallback_ad_available": true
}
```
* **ข้อกำหนดการแสดงผลฝั่ง Frontend:** หาก `sso_enabled == false` ให้ Frontend ซ่อนปุ่ม SSO และเข้าสู่โหมด Clean Standard Login ตามข้อ 5.2 โดยอัตโนมัติ (ไม่แสดงปุ่ม SSO และไม่แสดงข้อความเตือนใดๆ)

---

#### B.2 `POST /api/auth/sso/authorize-url` (สร้างความปลอดภัย PKCE S256)
* **การจำกัดสิทธิ์:** Public
* **พฤติกรรมระบบ:**
  1. ตรวจสอบว่า `ciam_sso_enabled == true` และ `ciam_break_glass_active == false` (หากปิดอยู่ ให้ตอบกลับ HTTP 503 เพื่อให้ Frontend สลับไปใช้ AD Password แทน)
  2. สุ่มสร้าง `code_verifier` ความยาวขั้นต่ำ 64 ตัวอักษร
  3. คำนวณ SHA-256 Digest แล้วเข้ารหัสแบบ Base64URL ได้เป็น `code_challenge` (ตาม RFC 7636)
  4. ส่งค่า `authorize_url`, `code_verifier`, และ `state` คืนให้ Frontend

**Request Body:**
```json
{
  "redirect_uri": "https://irm.windowasia.com/auth/callback"
}
```

**Response Example (200 OK):**
```json
{
  "authorize_url": "https://ciam.windowasia.com/oauth/authorize?response_type=code&client_id=irm-spoke-client&redirect_uri=https%3A%2F%2Firm.windowasia.com%2Fauth%2Fcallback&scope=openid+profile+email&state=state_1726038491&code_challenge=E9Mel-2Gq3...&code_challenge_method=S256",
  "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk...",
  "state": "state_1726038491"
}
```

---

#### B.3 `POST /api/auth/sso/callback` (แลกเปลี่ยน One-Time Code และออก Session ประจำระบบลูก)
* **การจำกัดสิทธิ์:** Public (เบราว์เซอร์ส่งมาหลัง Redirect จาก Central IAM)
* **ข้อกำหนดสำคัญระดับ Enterprise: รูปแบบการเข้าใช้งาน SSO (SSO Launch Modes):**

  1. **แบบที่ 1: Spoke-Initiated SSO (ผู้ใช้กดปุ่ม SSO จากหน้า Login ของระบบลูกเอง):**
     * เบราว์เซอร์เรียกขอ URL จาก `/api/auth/sso/authorize-url`
     * ระบบลูกสร้าง `code_verifier` (PKCE) และ `state` บันทึกผูกกับ Client Browser (ผ่าน `sessionStorage`, HttpOnly Session Cookie หรือ Backend Database ตามความเหมาะสม)
     * Redirect เบราว์เซอร์ไปยัง Central IAM เพื่อยืนยันตัวตน และรับ Authorization Code กลับมาที่ Callback พร้อมส่ง `code_verifier` และ `state` ไปตรวจสอบความถูกต้อง 100%

  2. **แบบที่ 2: Employee Portal Launch (ผู้ใช้คลิกเปิดแอปจากการ์ดใน Central IAM Portal):**
     
     * **🏆 แนวทางมาตรฐานแนะนำสูงสุด (RFC 9700 Compliant: Seamless SSO Initiation Bounce):**
       เพื่อป้องกันปัญหา CSRF และ Login Injection ตามคำแนะนำด้านความปลอดภัยระดับสากล [RFC 9700 §4.7](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.7) โดยยังคงประสบการณ์ผู้ใช้งานแบบ **คลิกครั้งเดียวเข้าใช้งานได้ทันที (Seamless 1-Click Launch):**
       1. การ์ดบน Central IAM Portal จะกำหนด Launch URL เป็น SSO Start Endpoint ของระบบลูก เช่น `https://spoke.windowasia.com/auth/start` (หรือเส้นทางที่ Spoke กำหนดไว้บนหน้าทะเบียนแอป)
       2. เมื่อผู้ใช้คลิกการ์ด เบราว์เซอร์จะเปิดไปยัง `/auth/start` ของระบบลูก
       3. ระบบลูกสร้างรายการ Login ใหม่ตามกลไกมาตรฐานเดิมของตนเอง (สร้าง `code_verifier`, `code_challenge` และ `state` ผูกกับ Session ของเบราว์เซอร์นั้น 100%)
       4. ระบบลูกสั่ง 302 Redirect เบราว์เซอร์ไปยัง Central IAM:  
          `${ciam_base_url}/oauth/authorize?response_type=code&client_id=...&redirect_uri=...&state=...&code_challenge=...&code_challenge_method=S256`
       5. **Zero-Prompt Auto-Approval:** เนื่องจากผู้ใช้ล็อกอินอยู่บนหน้า Central IAM Portal อยู่แล้ว CIAM จะตรวจสอบ Active Session Cookie บนเบราว์เซอร์ และทำ Auto-Approval ให้ทันทีโดยไม่ต้องถามรหัสผ่านซ้ำ
       6. CIAM ส่ง 302 Redirect พร้อม Authorization Code และ `state` เดิม กลับมายัง `/auth/callback` ของระบบลูก
       7. ระบบลูกตรวจสอบ `state` และ `code_verifier` ได้อย่างสมบูรณ์แบบตาม RFC 7636 ปลอดภัย ไร้ช่องโหว่ และผู้ใช้เข้าใช้งานระบบได้ภายในเวลาไม่เกิน 400ms

     * **แนวทางรอง (Legacy Direct Callback Launch):**
       กรณีที่ระบบลูกยังไม่ได้จัดเตรียม Endpoint เริ่มต้น SSO (`/auth/start`) และตั้งค่าให้ Portal ยิง Code ตรงเข้า Callback:
       * ในกรณีนี้ บนโดเมนของระบบลูกจะไม่มีค่า verifier หรือ state ผูกกับ Session มาก่อน
       * ⚠️ หากเลือกใช้แนวทางนี้ Backend ของระบบลูกต้องผ่อนปรนให้ฟิลด์ `code_verifier` และ `state` เป็น Optional และตรวจสอบความถูกต้องของ Token ผ่าน RS256 Signature และ Claims (`iss`, `aud`, `exp`) แทน
       * *ข้อแนะนำ:* แนะนำให้ทุกระบบลูกปรับมาใช้ **แนวทางมาตรฐาน RFC 9700 Seamless SSO Initiation Bounce (`/auth/start`)** เพื่อให้มีการผูก State กับเบราว์เซอร์อย่างถูกต้องตามมาตรฐานความปลอดภัยร่วมกัน

* **ขั้นตอนการประมวลผล (Backend-to-Backend):**
  0. **SSO Active & Break-Glass Guard:** ตรวจสอบว่า `ciam_sso_enabled == true` และ `ciam_break_glass_active == false` หากปิดอยู่ ให้ตอบกลับ `HTTP 503 Service Unavailable` และบันทึก `transaction_logs` หมวด `ciam_sso` ทันที เพื่อป้องกันไม่ให้ผู้ใช้แอบล็อกอินผ่าน Central IAM Portal เข้ามาได้ในขณะที่ระบบลูกปิดรับ SSO ชั่วคราว
  1. **แลกเปลี่ยน Authorization Code:** Backend ของระบบลูกส่งคำขอ HTTP POST ไปยัง `${ciam_base_url}/api/v1/oauth/token` พร้อม:
     * `grant_type`: `"authorization_code"`
     * `client_id`: ค่า Client ID ของตนเอง
     * `client_secret`: ค่า Client Secret ของตนเอง
     * `code`: รหัสที่ได้รับมา
     * `redirect_uri`: Callback URL ที่ลงทะเบียนไว้
     * `code_verifier`: (แนบเฉพาะกรณีที่มีค่าส่งมาจาก Frontend หากเปิดจาก Portal และไม่มีค่า verifier ให้ละเว้นฟิลด์นี้)
  2. ตรวจสอบ Asymmetric Signature ของ `id_token` ที่ได้รับด้วย Public Key จาก `${ciam_base_url}/.well-known/jwks.json` (อัลกอริทึม RS256)
  3. ตรวจสอบค่า Claims:
     * `iss` ต้องตรงกับ `ciam_base_url`
     * `aud` ต้องตรงกับ `client_id` ของตนเอง
     * `exp` ต้องยังไม่หมดอายุ
  4. **User Resolution & Auto-Provisioning:**
     * ค้นหาผู้ใช้จากตาราง `users` ด้วย `username` หรือ `email`
     * หากยังไม่เคยมีบัญชีในระบบลูก ให้สร้างบัญชีใหม่ทันที โดยผูกกับกลุ่มสิทธิ์ตามค่า `ciam_auto_provision_group` ใน System Settings และตั้งสถานะ `is_active = true`
  5. บันทึก `transaction_logs` หมวด `ciam_sso`
  6. ออก Session Token (JWT) ประจำระบบลูก และตอบกลับให้เบราว์เซอร์

**Request Body:**
```json
{
  "code": "auth_code_9a8b7c6d5e...",
  "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk...",
  "redirect_uri": "https://irm.windowasia.com/auth/callback",
  "state": "state_1726038491"
}
```
*(หมายเหตุ: `code_verifier` และ `state` เป็น Optional สามารถส่งเป็น string เปล่าหรือ null ได้เมื่อเป็นการเปิดใช้งานผ่าน Central IAM Portal)*

**Response Example (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 14,
    "username": "somchai.p",
    "full_name": "นายสมชาย พร้อมพงษ์",
    "email": "somchai.p@windowasia.com",
    "department": "Purchasing",
    "group_id": 2,
    "group_name": "PU Staff"
  }
}
```

---

#### B.4 `POST /api/auth/sso/break-glass-toggle` (สวิตช์ปลดระบบฉุกเฉินระดับ ISO 27001)
* **การจำกัดสิทธิ์:** ต้องตรวจสอบสิทธิ์ Admin พิเศษ (Security Administrator)
* **พฤติกรรมระบบ:**
  1. อัปเดตฟิลด์ `ciam_break_glass_active` ในตาราง `system_settings`
  2. บันทึก Audit Log ระดับความสำคัญสูงสุด
  3. ส่งแจ้งเตือนฉุกเฉินไปยัง Telegram / LINE Notify ของทีมผู้บริหารไอทีทันที
  4. เมื่อ Break-Glass เปิดอยู่ หน้าจอ Login ของระบบลูกจะอนุญาตให้พนักงานกรอกรหัสผ่าน Active Directory หรือ Local Admin เพื่อยิงตรงไปยัง `ciam_ad_gateway_url` ได้ทันที

**Request Body:**
```json
{
  "break_glass_active": true,
  "reason": "Central IAM Cloud Network Partition Maintenance"
}
```

---

### หมวด C: Directory Governance & Remote Provisioning Channel (CIAM สั่งการเข้ามาแบบ M2M)

> [!IMPORTANT]
> **ความปลอดภัยระดับองค์กร (Enterprise Security Constraints สำหรับ Mode A):**
> 1. **IP Whitelist:** ไฟร์วอลล์และ Reverse Proxy ของระบบลูกต้องอนุญาตเฉพาะ IP VPS ของ Central IAM: **`157.173.219.153`** (ระบบ CIAM จะแนบ Header `X-Forwarded-For: 157.173.219.153` มาด้วยเสมอ)
> 2. **Authentication Header:** ทุก Endpoint ในหมวด C ต้องส่ง HTTP Header: **`X-Management-API-Key: <SPOKE_API_KEY>`** (นำมาจากปุ่ม `🔑 M2M Key` ในหน้าทะเบียนระบบลูกของ Central IAM)
> 3. **Timestamp Verification:** CIAM จะส่ง `X-Request-Timestamp` เพื่อตรวจสอบและป้องกัน Replay Attacks
> 4. **Idempotent:** ทุก Endpoint ต้องรองรับการเรียกซ้ำได้โดยไม่เกิด Error ซ้ำซ้อน (Idempotent Execution)
>
> 💡 **ข้อกำหนดสำคัญสำหรับระบบ Mode C (เช่น MTPulse):**
> ระบบที่ใช้ **Mode C (On-Prem Outbound Agent)** ไม่ต้องพัฒนาหรือเปิด Endpoint ในหมวด C นี้ใดๆ ทั้งสิ้น การส่งรายชื่อบัญชี (Directory Sync) และการรับคำสั่งระงับสิทธิ์จะทำผ่าน **หมวด D (Reverse Heartbeat & Outbound Sync)** แทน 100% เพื่อความปลอดภัยโดยไม่ต้องเปิด Inbound Port

---

#### C.1 `GET /api/v1/directory/accounts` (Ping, Health Check & 04:00 AM Reconciliation)
* **วัตถุประสงค์:** 
  1. ใช้เป็น **Health Check & Latency Ping** แบบ Real-Time เมื่อ Central IAM ทดสอบสถานะระบบลูก
  2. ใช้สำหรับ **Auto-Reconciliation ประจำวันเวลา 04:00 น.** เพื่อดึงบัญชีผู้ใช้ทั้งหมดมาตรวจสอบ Ghost Account เปรียบเทียบกับ Active Directory
* **Query Parameters ที่รองรับ:**
  * `status`: กรองสถานะ เช่น `all` (ค่าเริ่มต้น), `active`, `inactive`
  * `department`: กรองตามแผนก (Optional)
  * `search`: ค้นหาชื่อหรือ username (Optional)
* **Response Example (200 OK):**
```json
{
  "application_name": "IRM (Incoming Raw Material)",
  "total_accounts": 2,
  "active_accounts": 2,
  "inactive_accounts": 0,
  "accounts": [
    {
      "id": 1,
      "username": "somchai.p",
      "full_name": "นายสมชาย พร้อมพงษ์",
      "email": "somchai.p@windowasia.com",
      "department": "Purchasing",
      "telegram_chat_id": "@somchai_p",
      "group_name": "PU User",
      "use_ad_auth": true,
      "is_active": true,
      "last_login_at": "2026-09-30T08:30:00Z",
      "created_at": "2026-09-20T10:00:00Z",
      "updated_at": "2026-09-30T08:30:00Z"
    },
    {
      "id": 2,
      "username": "local_supplier_01",
      "full_name": "Supplier Partner User",
      "email": "supplier01@partner.com",
      "department": "External Partner",
      "telegram_chat_id": null,
      "group_name": "Supplier Portal",
      "use_ad_auth": false,
      "is_active": true,
      "last_login_at": null,
      "created_at": "2026-09-25T14:20:00Z",
      "updated_at": "2026-09-25T14:20:00Z"
    }
  ]
}
```

---

#### C.2 `POST /api/v1/directory/accounts` (Remote User Provisioning)
* **วัตถุประสงค์:** เรียกใช้เมื่อ Super Admin สร้างหรือแจกจ่ายบัญชีผู้ใช้ใหม่จาก Central IAM ไปยังระบบลูก
* **Request Body:**
```json
{
  "username": "somchai.p",
  "full_name": "นายสมชาย พร้อมพงษ์",
  "email": "somchai.p@windowasia.com",
  "department": "Purchasing",
  "group_name": "PU User",
  "use_ad_auth": true,
  "created_by": "Central-IAM-Service"
}
```
* **พฤติกรรมระบบลูก:**
  1. ค้นหา `username` ในตาราง `users`
  2. หากยังไม่มี ให้บันทึกสร้างบัญชีใหม่ โดยกำหนดกลุ่มสิทธิ์ตาม `group_name` และตั้ง `is_active = true`
  3. หากมีอยู่แล้ว ให้คืนสถานะ `409 Conflict` (Central IAM จะถือว่ามีบัญชีอยู่แล้วและทำการ Link เข้าสู่ระบบ)
  4. บันทึกเหตุการณ์ลงใน `transaction_logs`
* **Response Example (201 Created):**
```json
{
  "success": true,
  "id": 15,
  "username": "somchai.p",
  "message": "Account 'somchai.p' created successfully.",
  "group_name": "PU User",
  "is_active": true,
  "created_at": "2026-09-30T22:00:00Z"
}
```

---

#### C.3 `PATCH /api/v1/directory/accounts/{username}/status` (1-Click Offboarding & Reactivate)
* **วัตถุประสงค์:** 
  1. **1-Click Offboarding:** ตัดสิทธิ์และระงับบัญชีทันทีเมื่อพนักงานลาออกหรือพ้นสภาพ
  2. **Reactivate:** คืนสิทธิ์การใช้งานเมื่อพนักงานกลับมาปฏิบัติหน้าที่
* **Request Body:**
```json
{
  "is_active": false,
  "reason": "1-Click Offboarding via Central Identity Management",
  "updated_by": "Central-IAM-Service"
}
```
* **พฤติกรรมระบบลูก (CRITICAL):**
  1. อัปเดต `is_active = false` (หรือ `true` กรณีคืนสิทธิ์)
  2. **Revoke Active Sessions ทันที (เมื่อ is_active = false):** ล้าง Refresh Token และยกเลิก Session ของผู้ใช้นี้ทันที เพื่อให้หลุดจากระบบแบบ Real-time
  3. บันทึก `transaction_logs` หมวด `ciam_sso` ระบุเหตุการณ์ระงับสิทธิ์หรือคืนสิทธิ์
* **Response Example (200 OK):**
```json
{
  "username": "somchai.p",
  "is_active": false,
  "message": "Account status updated successfully",
  "updated_at": "2026-09-30T22:00:00Z"
}
```

---

#### C.4 การจัดการผู้ใช้ Local Account (Non-AD Users) และข้อยกเว้นการใช้งาน App Portal
* **ที่มาและความจำเป็น:**
  * ในองค์กรจริง อาจมีผู้ใช้บางกลุ่มที่**ไม่ได้อยู่ใน Active Directory** แต่ถูกสร้างขึ้นโดยตรงในระบบลูก เช่น ผู้ใช้งานชั่วคราว, ช่างภายนอก หรือ Supplier ในระบบ IRM
  * บัญชีเหล่านี้จะมีแฟล็ก `use_ad_auth: false` ในตาราง `users`
* **มาตรฐานการเชื่อมต่อ:**
  1. เมื่อ Central IAM สั่ง Sync ผ่าน `GET /api/v1/directory/accounts` ระบบลูกจะส่งฟิลด์ `use_ad_auth: false` กลับมาในรายการบัญชี
  2. ฝั่ง Central IAM จะระบุบัญชีนี้เป็น **"Local Account ใน Spoke"** โดยอัตโนมัติ
  3. ผู้ดูแลระบบสามารถตั้งรหัสผ่าน Portal Password หรือสร้าง **"ข้อยกเว้นการเชื่อมโยงตัวตน (Identity Exception)"** ในหน้า Portal & Directory ให้กับผู้ใช้รายนี้ได้
  4. เมื่อผู้ใช้ดังกล่าวล็อกอินเข้า Central IAM Portal ด้วยรหัสผ่าน Portal:
     * **หน้า App Portal จะแสดงเฉพาะแอปที่เขามีสิทธิ์ (เช่น IRM) เท่านั้น** และซ่อนระบบอื่นที่ไม่มีสิทธิ์ออกไปโดยอัตโนมัติ
     * ผู้ใช้สามารถคลิกเข้าสู่ระบบลูกผ่าน Single Sign-On ได้อย่างราบรื่น
  5. หากผู้ใช้รายเดียวกันมีบัญชีใน 2 ระบบลูกที่ไม่ได้ใช้ AD ทั้งคู่ และรหัสผ่านไม่ตรงกัน ผู้ดูแลระบบสามารถใช้ฟังก์ชัน **"รวมตัวตน (Unified Identity Link)"** ในหน้าบัญชีผู้ใช้ Central IAM เพื่อผูกบัญชีทั้งสองเข้ากับ Portal Identity เดียวกันได้อย่างปลอดภัย

### หมวด D: Reverse Heartbeat & Outbound Sync Channel (สำหรับ Mode C: On-Premise Spoke Applications)

หมวดนี้ออกแบบมาสำหรับระบบลูกที่ติดตั้งอยู่ภายในเครือข่ายองค์กร (On-Premise / Local LAN เช่น MTPulse, WMS, ERP ในโรงงาน) ที่**ไม่มี Inbound Public Tunnel จากภายนอก** แต่ต้องการให้:
1. Central IAM สามารถ**กวาดรายชื่อผู้ใช้ทั้งหมด (Directory Sync)** มาเก็บไว้เพื่อตรวจสอบสิทธิ์และการจัดการแบบศูนย์กลาง
2. สามารถสั่ง**ระงับสิทธิ์บัญชีผู้ใช้ (1-Click Offboarding)** หรือคืนสิทธิ์ได้จาก Central IAM Cloud
3. Central IAM แสดงสถานะ **🟢 ออนไลน์ / 🔴 ออฟไลน์** ได้อย่างแท้จริง ผ่านระบบ **Dead Man's Switch Heartbeat** โดยไม่ต้องเจาะไฟร์วอลล์ออฟฟิศ

---

#### D.1 สถาปัตยกรรมการทำงาน (Reverse Heartbeat & Pull Pattern)
แทนที่เซิร์ฟเวอร์ CIAM บน Cloud จะยิง Inbound เข้ามา (ซึ่งทำไม่ได้เพราะติด NAT/Firewall):
1. **ระบบลูก (Spoke) เป็นฝ่ายยิง Outbound HTTPS 443 ออกไปหา CIAM เป็นระยะ:** (ค่าแนะนำ: ทุก 120 วินาที / 2 นาที)
2. **รายงานตัว (Heartbeat):** แจ้ง CIAM ว่าเครื่องยังทำงานอยู่ปกติ CIAM จะอัปเดตสถานะเป็น `ONLINE`
3. **ส่งผลลัพธ์คำสั่งเดิม (Command Acknowledgment):** หากรอบที่แล้วได้รับคำสั่งระงับสิทธิ์ ให้ส่งสถานะกลับว่าระงับสิทธิ์ในฐานข้อมูลตนเองสำเร็จแล้ว (`COMPLETED`)
4. **ดึงคำสั่งใหม่กลับมาทำ (Pull Pending Commands):** CIAM จะส่งรายการคำสั่งที่รออยู่ (เช่น `DISABLE_USER`) กลับมาใน Response เพื่อให้ Spoke นำไป execute ในเครื่องตนเอง
5. **กวาดรายชื่อขึ้น Cloud (Push Directory Sync):** ส่งรายชื่อบัญชีทั้งหมด (`accounts`) ขึ้นมาอัปเดตบน CIAM (ส่งวันละครั้ง หรือส่งเมื่อมีการสร้าง User ภายใน)

---

#### D.2 `POST https://ciam.windowasia.com/api/v1/agent/heartbeat` (เอนด์พอยต์รายงานตัวบน CIAM)
* **ผู้เรียก:** ฝั่งระบบลูก (Spoke Agent Background Worker)
* **ผู้รับ:** Central IAM Engine บน Cloud
* **Authentication Headers:**
  * `Content-Type: application/json`
  * `X-Spoke-Client-ID`: ค่า Client ID ของระบบลูก (เช่น `mtpulse-spoke-client`)
  * `X-Spoke-API-Key`: ค่า M2M Secret API Key (หรือ Client Secret ที่ผูกไว้บน CIAM)
  * `X-Request-Timestamp`: Unix Timestamp (วินาที)

##### รูปแบบ Request Body:
```json
{
  "app_code": "mtpulse",
  "status": "HEALTHY",
  "app_version": "1.0.4",
  "sync_type": "HEARTBEAT",
  "command_results": [
    {
      "command_id": "cmd_a1b2c3d4",
      "action": "DISABLE_USER",
      "username": "somchai.k",
      "status": "COMPLETED",
      "message": "User deactivated successfully in local SQLite/PostgreSQL database"
    }
  ],
  "accounts": [
    {
      "username": "chaiwat.n",
      "full_name": "Chaiwat Nilawan",
      "email": "chaiwat.n@windowasia.com",
      "department": "IT",
      "role": "PU Staff",
      "is_active": true
    }
  ]
}
```
> **หมายเหตุเรื่อง Accounts Payload:** ฟิลด์ `accounts` ให้ส่งเฉพาะเมื่อ `sync_type == "FULL_SYNC"` (เช่น วันละครั้ง) เพื่อประหยัด Bandwidth ในรอบ Heartbeat ปกติทุก 2 นาทีให้ส่ง `sync_type: "HEARTBEAT"` และละเว้นฟิลด์ `accounts` ได้

##### รูปแบบ Response Example (200 OK):
```json
{
  "status": "ACKNOWLEDGED",
  "app_code": "mtpulse",
  "server_time": "2026-10-08T10:00:00Z",
  "next_heartbeat_seconds": 120,
  "pending_commands": [
    {
      "command_id": "cmd_prov_9a8b",
      "action": "PROVISION_USER",
      "username": "ronnakorn.p",
      "reason": "Auto-Reconciliation: Account assigned on Central IAM for วิเคราะห์การขาย Modern Trade",
      "issued_at": "2026-10-08T10:00:00Z"
    },
    {
      "command_id": "cmd_e5f6g7h8",
      "action": "DISABLE_USER",
      "username": "resigned_user_01",
      "reason": "1-Click Offboarding via Central IAM",
      "issued_at": "2026-10-08T09:58:30Z"
    },
    {
      "command_id": "cmd_sync_0912",
      "action": "REQUEST_FULL_SYNC",
      "username": "ALL_ACCOUNTS",
      "reason": "On-demand Full Directory Sync triggered from Central IAM (or 04:00 AM Reconciliation)",
      "issued_at": "2026-10-08T10:00:00Z"
    }
  ],
  "assigned_accounts": [
    {
      "username": "chaiwat.n",
      "full_name": "Chaiwat Nilawan",
      "email": "chaiwat.n@windowasia.com",
      "department": "Purchasing",
      "role": "System Admin",
      "is_active": true
    },
    {
      "username": "ronnakorn.p",
      "full_name": "Ronnakorn Pattarakrittanon",
      "email": "ronnakorn.p@windowasia.com",
      "department": "Supply Chain Analysis",
      "role": "Viewer",
      "is_active": true
    }
  ],
  "message": "Heartbeat received for วิเคราะห์การขาย Modern Trade. 3 pending command(s) dispatched."
}
```

##### รายการคำสั่งมาตรฐานใน Pending Commands Queue (`action`):
| Action | ค่า `username` | คำอธิบาย & พฤติกรรมที่ระบบลูกต้องปฏิบัติ |
| :--- | :---: | :--- |
| `PROVISION_USER` | ชื่อ Username พนักงาน | **คำสั่งสร้างบัญชีผู้ใช้ใหม่จาก CIAM (Two-Way Reconciliation):** เมื่อ CIAM มีการมอบสิทธิ์การเข้าใช้งาน Spoke ให้แก่พนักงาน แต่ใน Spoke ยังไม่มีบัญชีนี้ Agent ของ Spoke ต้องสร้างบัญชีนี้ลงในฐานข้อมูลภายในทันที โดยกำหนดสิทธิ์เริ่มต้นตามค่า `ciam_auto_provision_group` (เช่น `Viewer`) และตั้งสถานะ `is_active = true` เพื่อให้จำนวนบัญชีตรงกันทันทีโดยไม่ต้องรอพนักงานล็อกอิน |
| `DISABLE_USER` | ชื่อ Username พนักงาน | สั่งระงับสิทธิ์บัญชีผู้ใช้ในระบบลูก (`is_active = false`) และ Revoke Session/Refresh Token ทั้งหมดทันที |
| `ENABLE_USER` | ชื่อ Username พนักงาน | สั่งเปิดหรือคืนสิทธิ์การใช้งานบัญชีผู้ใช้ในระบบลูก (`is_active = true`) |
| `REQUEST_FULL_SYNC` | `"ALL_ACCOUNTS"` | **คำสั่งขอ Full Directory Sync จาก CIAM:** เกิดขึ้นเมื่อ Admin กดปุ่ม "⚡ ซิงค์ข้อมูล" บน Central IAM หรือรอบตรวจสอบ 04:00 น. Reconciliation โดย Agent ต้องดึงรายชื่อผู้ใช้ทั้งหมดจากฐานข้อมูลภายใน แล้วส่งคืนใน Heartbeat รอบถัดไปด้วย `sync_type: "FULL_SYNC"` พร้อม Payload `accounts: [...]` |

---

#### D.3 กฎเกณฑ์วงจรชีวิตคำสั่งและความปลอดภัย (Command Lifecycle & Safety Governance)

##### 1. วงจรชีวิตสถานะคำสั่งแบบ Asynchronous (Asynchronous Deprovisioning Lifecycle)
เนื่องจากการเชื่อมต่อ Mode C เป็นการที่เซิร์ฟเวอร์ On-Premise ยิง Outbound ออกมาติดต่อ CIAM การส่งคำสั่งจึงเป็นแบบ Asynchronous ซึ่งมีขั้นตอนดังนี้:
1. **`PENDING` (รอส่งคำสั่ง):** เมื่อผู้ดูแลระบบคลิก 1-Click Offboard บน Central IAM คำสั่งจะถูกบันทึกเข้าสู่ Command Queue ของแอปพลิเคชันนั้น
2. **`SENT` (ส่งคำสั่งแล้ว):** เมื่อ Agent ของระบบลูกยิง Heartbeat เข้ามา CIAM จะส่งคำสั่งในคิวออกไปพร้อม Response และเปลี่ยนสถานะคำสั่งเป็น `SENT`
3. **`COMPLETED` (ระบบลูกดำเนินการสำเร็จ):** Agent นำคำสั่งไปประมวลผล อัปเดตฐานข้อมูล ยกเลิก Session และรายงานผล `status: "COMPLETED"` กลับมาใน Heartbeat รอบถัดไป CIAM จึงจะบันทึกสถานะ Success และปิด Job คำสั่งนั้น
4. **`FAILED` (ระบบลูกดำเนินการไม่สำเร็จ):** หากเกิดข้อผิดพลาดในการประมวลผล หรือคำสั่งขัดต่อนโยบายความปลอดภัยของระบบลูก Agent จะรายงาน `status: "FAILED"` พร้อมระบุ `message` เหตุผล
* **ระยะเวลาประมวลผล (SLA):** ในสภาวะเครือข่ายปกติ กระบวนการจะเสร็จสิ้นภายใน **รอบ Heartbeat ไม่เกิน 2 นาที + เวลาประมวลผลภายในระบบลูก** หากเครือข่ายสำนักงานขัดข้อง คำสั่งจะรออยู่ในคิวจนกว่า Agent จะติดต่อกลับมา
* **การแสดงผลบนหน้าจอ Central IAM:** หน้าจอ Central IAM จะแยกแยะระหว่างการตัดสิทธิ์ Single Sign-On ส่วนกลาง (ตัดสิทธิ์ทันที) กับสถานะการปิดบัญชีภายในระบบลูก (แสดงสถานะตามจริง: "รอส่งคำสั่งไปยัง Agent" ➔ "ส่งคำสั่งแล้ว" ➔ "ระบบลูกยืนยันสำเร็จ")

##### 2. นโยบายการปกป้องบัญชี Local Admin ฉุกเฉิน (Local & Break-Glass Administrator Protection)
Central IAM ตระหนักและสนับสนุนอย่างยิ่งให้นโยบายความปลอดภัยภายในของระบบลูกมีกลไกป้องกันตนเอง (Local Guardrails):
* ระบบลูก**ต้องไม่อนุญาต**ให้คำสั่งภายนอกระงับสิทธิ์บัญชีผู้ดูแลระบบฉุกเฉิน (Break-Glass / Emergency Local Administrator) หรือบัญชี Admin คนสุดท้ายของระบบลูกได้
* หาก Central IAM ส่งคำสั่ง `DISABLE_USER` ไปยังบัญชีที่ได้รับการปกป้องดังกล่าว Agent ของระบบลูกสามารถปฏิเสธคำสั่ง โดยส่งผลลัพธ์:
  ```json
  {
    "command_id": "cmd_e5f6g7h8",
    "action": "DISABLE_USER",
    "username": "emergency_admin",
    "status": "FAILED",
    "message": "Protected account: Cannot disable emergency local administrator"
  }
  ```
* **การจัดการฝั่ง Central IAM:** Engine ของ Central IAM รองรับสถานะ `FAILED` นี้โดยสมบูรณ์ จะบันทึกเหตุผลลงใน Audit Trail (`IamAuditLog`) และแสดงข้อความเตือนให้ผู้ดูแลระบบ CIAM ทราบอย่างชัดเจน โดยไม่ถือว่าเป็น Error ของระบบเชื่อมต่อ

##### 3. กฎเกณฑ์การตรวจจับ Online / Offline (Dead Man's Switch)
* **ความถี่ Heartbeat:** แนะนำให้ Spoke ยิง Heartbeat ทุก **120 วินาที (2 นาที)**
* **เงื่อนไขสถานะออนไลน์ (`ONLINE`):** เมื่อ CIAM ได้รับ Heartbeat ล่าสุดภายใน **300 วินาที (5 นาที)**
* **เงื่อนไขสถานะออฟไลน์ (`OFFLINE`):** หากเซิร์ฟเวอร์ On-Premise ไฟดับ, อินเทอร์เน็ตสำนักงานขัดข้อง หรือ Agent หยุดทำงานเกิน **5 นาที** CIAM จะปรับสถานะของระบบนี้เป็น **`🔴 ออฟไลน์`** โดยอัตโนมัติ และปุ่มบนหน้า Employee Portal จะถูกล็อกเป็น *"ระบบปิดปรับปรุงชั่วคราว (Offline)"* ทันที เพื่อป้องกันพนักงานเข้าใช้งานระบบที่ล่ม

---

#### D.4 มาตรฐานการซิงก์แบบสองทางและการสร้างปุ่มซิงก์ทันทีบนหน้าจอ Spoke (Two-Way Directory Reconciliation & Mandatory Immediate Sync Button)

เพื่อให้การจัดการบัญชีผู้ใช้งานระหว่าง Central IAM และระบบลูก Mode C ทำงานสอดประสานกันได้อย่างสมบูรณ์เทียบเท่าระบบ Cloud (Two-Way Equivalence):

##### 1. หลักการทำงาน Two-Way Reconciliation สำหรับ Mode C
1. **เมื่อมีการเพิ่มหรือมอบสิทธิ์บัญชีบน Central IAM:**  
   เช่น Admin กำหนดสิทธิ์ให้ `Ronnakorn.P` เข้าใช้งาน MTPulse ในระบบ CIAM (แสดงแท็ก `• MTPULSE` บนหน้าจอ CIAM)
2. **การตรวจจับความแตกต่าง (Reconciliation Diff):**  
   เมื่อ Spoke ส่งรายชื่อบัญชีขึ้นมาในรอบ Full Sync หรือ Heartbeat:
   * **กรณี CIAM มี แต่ Spoke ยังไม่มี:** CIAM จะส่งรายชื่อบัญชีที่ได้รับสิทธิ์ในฟิลด์ `assigned_accounts` และออกคำสั่ง **`PROVISION_USER`** ส่งกลับไปใน `pending_commands`
   * **กรณีพนักงานถูกระงับสิทธิ์บน CIAM (ลาออก / ย้ายแผนก):** หากใน Spoke บัญชียังเปิดใช้งานอยู่ (`is_active = true`) CIAM จะส่งคำสั่ง **`DISABLE_USER`** กลับไปสั่งปิดทันที
   * **กรณีพนักงานได้รับการเปิดสิทธิ์คืน:** หากใน Spoke บัญชีถูกปิดอยู่ CIAM จะส่งคำสั่ง **`ENABLE_USER`** กลับไปเปิดใช้งาน
3. **การประมวลผลฝั่ง Spoke (Local Auto-Creation):**  
   เมื่อ Spoke ได้รับคำสั่ง `PROVISION_USER`:
   * ให้สร้างบัญชีนั้นลงในตาราง `users` ของฐานข้อมูลตนเองทันที
   * กำหนด Role เริ่มต้นตามค่า `ciam_auto_provision_group` (เช่น `Viewer`)
   * ตั้งสถานะ `active = true`
   * **ผลลัพธ์:** ทั้ง Central IAM และ Spoke จะมี **จำนวนบัญชีผู้ใช้เท่ากัน และสถานะ Active/Inactive ของแต่ละบัญชีตรงกัน 100% ในทันที** โดยไม่จำเป็นต้องรอให้พนักงานคนนั้นกดล็อกอิน SSO เข้ามาก่อน

##### 2. ข้อบังคับหน้าจอ Spoke UI: ปุ่ม "ซิงก์บัญชีผู้ใช้กับ CIAM ทันที" (Mandatory Immediate Sync Button)
ระบบลูกที่เป็น Mode C **ต้องมีปุ่มสำหรับสั่งซิงก์ข้อมูลทันทีบนหน้าจอ System Setting** (ในแท็บ User Management หรือแท็บ Central IAM / AD):

* **ข้อความบนปุ่ม:** **`[ ⚡ ซิงก์บัญชีผู้ใช้กับ CIAM ทันที ]`** (Immediate Account Sync)
* **พฤติกรรมเมื่อผู้ดูแลระบบกดปุ่ม:**
  1. Frontend เรียก Internal API ของตนเอง เช่น `POST /api/settings/ciam-agent/sync-now`
  2. Spoke Backend สั่งให้ Agent ทำงานรอบพิเศษทันทีแบบ Synchronous (ไม่ต้องรอรอบเวลา 120 วินาที) โดยกำหนด `sync_type: "FULL_SYNC"`
  3. Agent ส่งรายชื่อบัญชีทั้งหมดที่มีในเครื่องขึ้นไปรายงานตัวที่ CIAM
  4. CIAM คำนวณความต่าง (Diff) และส่งคำสั่ง `PROVISION_USER`, `DISABLE_USER`, `ENABLE_USER` พร้อม `assigned_accounts` กลับมาใน Response ทันที
  5. Spoke Backend นำคำสั่งไปสร้างบัญชีที่ขาดลงฐานข้อมูล และปรับสถานะ Active/Inactive ให้ตรงกับ CIAM ทันที
  6. Frontend ทำการรีเฟรชตารางรายชื่อผู้ใช้ และแสดง Alert แจ้งผลสำเร็จ เช่น:  
     *"ซิงก์ข้อมูลกับ Central IAM สำเร็จ: ปรับปรุงสถานะตรงกัน 100% (สร้างใหม่ 1 บัญชี, ปรับสถานะ 0 บัญชี)"*

---

#### D.5 ตัวอย่างโค้ดมาตรฐานสำหรับ Developer ระบบลูก (Production-Ready Python Agent)
ทีมพัฒนา Spoke สามารถนำไฟล์สคริปต์นี้ (เช่น `ciam_agent.py`) ไปวางในโปรเจกต์ของระบบตนเอง และตั้งเวลารันได้ทันที:

```python
\"\"\"
ciam_agent.py — Reverse Heartbeat & Command Worker for On-Premise Spoke Applications
Organization: Window Asia Public Company Limited
Supported Mode: Mode C (Outbound Reverse Heartbeat & Command Queue)
\"\"\"

import time
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ciam_spoke_agent")

# --- 1. การกำหนดค่าเชื่อมต่อ (ดึงจาก system_settings ใน DB หรือ Config File) ---
CIAM_BASE_URL = "https://ciam.windowasia.com"
APP_CODE = "mtpulse"                            # รหัสระบบลูกตัวพิมพ์เล็ก
SPOKE_CLIENT_ID = "mtpulse-spoke-client"        # Client ID ที่ลงทะเบียนไว้บน CIAM
SPOKE_API_KEY = "sec_mtpulse_mgmt_xxxxxxxxx"   # M2M API Key หรือ Client Secret
HEARTBEAT_INTERVAL = 120                       # วินาที (2 นาที)

def execute_local_command(action: str, username: str) -> tuple[bool, str]:
    \"\"\"
    ฟังก์ชันสำหรับจัดการฐานข้อมูลภายในระบบลูกเมื่อได้รับคำสั่งจาก CIAM
    * แก้ไขฟังก์ชันนี้ให้ปรับปรุงสถานะผู้ใช้ในตาราง users หรือฐานข้อมูลจริงของระบบคุณ *
    \"\"\"
    try:
        logger.info(f"⚡ กำลังดำเนินการคำสั่ง '{action}' สำหรับผู้ใช้ '{username}' ในระบบภายใน...")
        
        if action == "DISABLE_USER":
            # 🛡️ Local Admin & Safety Protection: ป้องกันการปิดบัญชีผู้ดูแลระบบฉุกเฉิน
            PROTECTED_ACCOUNTS = {"admin", "superadmin", "emergency_admin", "local_admin"}
            if username.lower() in PROTECTED_ACCOUNTS:
                logger.warning(f"🛡️ ปฏิเสธคำสั่ง DISABLE_USER: บัญชี '{username}' เป็น Emergency Local Administrator ประจำระบบลูก")
                return False, f"Protected account: Cannot disable emergency local administrator '{username}'"

            # ตัวอย่าง SQL หรือ ORM ดำเนินการระงับสิทธิ์จริงในระบบลูก:
            # db.execute("UPDATE users SET is_active = FALSE WHERE username = ?", (username,))
            # db.execute("DELETE FROM user_active_sessions WHERE username = ?", (username,))
            return True, f"User '{username}' disabled and sessions revoked successfully."
            
        elif action == "ENABLE_USER":
            # db.execute("UPDATE users SET is_active = TRUE WHERE username = ?", (username,))
            return True, f"User '{username}' enabled successfully."
            
        return False, f"Unknown action: {action}"
    except Exception as exc:
        logger.error(f"❌ ดำเนินการคำสั่งไม่สำเร็จ: {exc}")
        return False, str(exc)

def fetch_local_accounts() -> list[dict]:
    \"\"\"
    ฟังก์ชันดึงรายชื่อผู้ใช้ทั้งหมดจากฐานข้อมูลภายใน เพื่อส่งขึ้นไปกวาด Sync บน CIAM
    (เรียกเฉพาะเมื่อต้องการทำ Full Directory Sync)
    \"\"\"
    # ตัวอย่างคืนค่าบัญชี:
    return [
        # {"username": "somchai", "full_name": "สมชาย ใจดี", "email": "somchai@wa.com", "role": "Staff", "is_active": True}
    ]

def run_agent_cycle(is_full_sync: bool = False, previous_results: list = None) -> list:
    \"\"\"
    ยิง Outbound POST 1 รอบไปยัง Central IAM:
    1. ส่ง Heartbeat
    2. ส่งผลลัพธ์คำสั่งรอบก่อนหน้า (ถ้ามี)
    3. รับคำสั่งใหม่ไปประมวลผล
    \"\"\"
    endpoint = f"{CIAM_BASE_URL}/api/v1/agent/heartbeat"
    headers = {
        "Content-Type": "application/json",
        "X-Spoke-Client-ID": SPOKE_CLIENT_ID,
        "X-Spoke-API-Key": SPOKE_API_KEY,
        "X-Request-Timestamp": str(int(time.time()))
    }
    payload = {
        "app_code": APP_CODE,
        "status": "HEALTHY",
        "sync_type": "FULL_SYNC" if is_full_sync else "HEARTBEAT",
        "command_results": previous_results or []
    }
    
    if is_full_sync:
        payload["accounts"] = fetch_local_accounts()

    try:
        res = requests.post(endpoint, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            logger.info(f"✅ Heartbeat สำเร็จ: ตอบรับจาก CIAM ({data.get('server_time')})")
            
            # ตรวจสอบและประมวลผลคำสั่งที่ส่งมาจาก CIAM
            pending_commands = data.get("pending_commands", [])
            new_results = []
            should_sync_next = False
            for cmd in pending_commands:
                cmd_id = cmd["command_id"]
                action = cmd["action"]
                target_user = cmd["username"]

                # รองรับคำสั่งขอ Full Sync จากหน้าจอ CIAM หรือรอบ 04:00 น.
                if action == "REQUEST_FULL_SYNC":
                    logger.info("⚡ ได้รับคำสั่ง REQUEST_FULL_SYNC: เตรียมส่งข้อมูลบัญชีทั้งหมดในรอบถัดไป")
                    should_sync_next = True
                    new_results.append({
                        "command_id": cmd_id,
                        "action": action,
                        "username": target_user,
                        "status": "COMPLETED",
                        "message": "Full sync command acknowledged. Directory inventory will be pushed."
                    })
                else:
                    success, msg = execute_local_command(action, target_user)
                    new_results.append({
                        "command_id": cmd_id,
                        "action": action,
                        "username": target_user,
                        "status": "COMPLETED" if success else "FAILED",
                        "message": msg
                    })
            return new_results, should_sync_next
        else:
            logger.warning(f"⚠️ CIAM ตอบกลับสถานะ {res.status_code}: {res.text[:200]}")
            return previous_results or [], False
    except Exception as exc:
        logger.error(f"❌ ไม่สามารถเชื่อมต่อไปยัง Central IAM: {exc}")
        return previous_results or [], False

def main():
    logger.info(f"🚀 เริ่มต้นการทำงาน Window Asia CIAM Agent สำหรับระบบ '{APP_CODE}'")
    
    # รอบแรกสุด: ทำ Full Sync กวาดบัญชีขึ้น CIAM ทันทีที่สตาร์ท
    pending_results, force_sync = run_agent_cycle(is_full_sync=True)
    
    sync_counter = 0
    while True:
        try:
            time.sleep(HEARTBEAT_INTERVAL)
            sync_counter += 1
            
            # กวาด Full Directory Sync ทุกๆ 720 รอบ (ประมาณ 24 ชั่วโมง) หรือเมื่อได้รับคำสั่ง REQUEST_FULL_SYNC
            is_daily_sync = (sync_counter % 720 == 0) or force_sync
            
            pending_results, force_sync = run_agent_cycle(is_full_sync=is_daily_sync, previous_results=pending_results)
        except KeyboardInterrupt:
            logger.info("หยุดการทำงานของ Agent")
            break
        except Exception as exc:
            logger.error(f"ข้อผิดพลาดใน Loop: {exc}")
            time.sleep(30)

if __name__ == "__main__":
    main()
```

---

#### D.5 การตั้งเวลาให้ Agent ทำงานอัตโนมัติ (Deployment Options)

Developer สามารถเลือกติดตั้ง Agent ให้ทำงานตลอด 24 ชั่วโมงได้ 3 วิธี:

##### วิธีที่ 1: ติดตั้งเป็น Linux Systemd Service (แนะนำสำหรับ Linux Server)
สร้างไฟล์ `/etc/systemd/system/ciam-agent.service`:
```ini
[Unit]
Description=Window Asia Central IAM Spoke Reverse Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/mtpulse
ExecStart=/var/www/mtpulse/venv/bin/python /var/www/mtpulse/ciam_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
เปิดใช้งาน service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ciam-agent
sudo systemctl start ciam-agent
```

##### วิธีที่ 2: รันผ่าน Crontab บน Linux
```bash
# ส่ง Heartbeat ทุก 2 นาที
*/2 * * * * cd /var/www/mtpulse && /var/www/mtpulse/venv/bin/python ciam_agent.py --once >> /var/log/ciam_agent.log 2>&1
```

##### วิธีที่ 3: ตั้งเวลาผ่าน Windows Task Scheduler (สำหรับ Windows Server)
* Action: `Start a program`
* Program/script: `python.exe` (หรือ `pythonw.exe` เพื่อซ่อนหน้าต่าง cmd)
* Add arguments: `C:\inetpub\wwwroot\mtpulse\ciam_agent.py`
* Trigger: `At startup` หรือ `Daily, repeat every 2 minutes indefinitely`

---

## 4. มาตรฐานการบันทึก Audit Logs ในระบบลูก (Log Matrix Specification)

ระบบลูกทุกระบบต้องบันทึกเหตุการณ์ลงในตาราง `transaction_logs` ตามเงื่อนไขดังต่อไปนี้อย่างครบถ้วน:

| Event Code | Category | Action | Status | Message ภาษาไทย | Triggered By | ข้อมูลในฟิลด์ Details (JSON String) |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **SSO-01** | `ciam_sso` | `login_success` | `success` | เข้าสู่ระบบผ่าน Central IAM SSO สำเร็จ: ผู้ใช้ '{username}' | `user:{username}` | `{"username":"...", "ip":"...", "ciam_issuer":"...", "auth_method":"OIDC_PKCE_S256", "roles":{...}}` |
| **SSO-02** | `ciam_sso` | `login_failed` | `failed` | การยืนยันตัวตน SSO ล้มเหลว: {สาเหตุ} | `user:{username}` | `{"error":"SignatureVerificationFailed", "ip":"...", "detail":"Token expired or tampered"}` |
| **SSO-03** | `ciam_sso` | `auto_provision_user` | `info` | สร้างบัญชีผู้ใช้ใหม่อัตโนมัติจาก Central IAM: '{username}' | `system:ciam` | `{"username":"...", "email":"...", "group_assigned":"PU Staff", "claims":{...}}` |
| **SSO-04** | `ciam_sso` | `account_deactivated` | `warning` | ปฏิเสธการเข้าสู่ระบบ: บัญชีพนักงาน '{username}' ถูกระงับสิทธิ์ในระบบนี้ | `user:{username}` | `{"username":"...", "ip":"...", "reason":"is_active is false"}` |
| **BG-01** | `security_break_glass` | `toggle_break_glass` | `warning` / `success` | สลับสถานะระบบ Break-Glass: {ENABLED/DISABLED} | `user:{admin_user}` | `{"break_glass_active":true, "reason":"...", "ip":"...", "prev_state":false}` |
| **BG-02** | `security_break_glass` | `fallback_ad_login` | `success` | เข้าสู่ระบบผ่าน AD Gateway สำรองในช่วง Break-Glass: '{username}' | `user:{username}` | `{"username":"...", "gateway":"http://172.18.0.1:3100", "ip":"..."}` |
| **CFG-01**| `system_setting` | `update_ciam_settings`| `success` | แก้ไขการตั้งค่าระบบ Central IAM SSO | `user:{admin_user}` | `{"changed_fields":["ciam_base_url","ciam_session_ttl_minutes"], "ip":"..."}` |

---

## 5. มาตรฐานหน้าจอจัดการบน Frontend (UI Guidelines)

### 5.1 หน้าจอ System Settings (แท็บ "Central IAM SSO")
ให้ผู้พัฒนาฝั่ง Frontend สร้างฟอร์มการตั้งค่าในหน้าผู้ดูแลระบบ ประกอบด้วย:

1. **การ์ดสถานะการเชื่อมต่อ (Health & Status Banner):**
   * ป้ายไฟสถานะ: `🟢 เชื่อมต่อปกติ (Online)` หรือ `🔴 ไม่สามารถเชื่อมต่อได้ (Offline)`
   * ปุ่ม `[ ⚡ ทดสอบการเชื่อมต่อไปยัง Central IAM ]` เรียกใช้ API `POST /api/settings/ciam-sso/test-connection`
2. **ฟิลด์แบบฟอร์มการตั้งค่า:**
   * `Central IAM Base URL` (Text Input, เช่น `https://ciam.windowasia.com`)
   * `OIDC Client ID` (Text Input, เช่น `irm-spoke-client`)
   * `OIDC Client Secret` (Password Input มีปุ่มคลิกเพื่อเปิดดู และปุ่มสลับเพื่อกรอก Secret ใหม่)
   * `Active Directory Gateway URL` (Text Input, ค่าเริ่มต้น `http://172.18.0.1:3100`)
   * `กลุ่มสิทธิ์เริ่มต้น (Default Group)` (Dropdown รายชื่อ Group เช่น PU Staff, User)
   * `สวิตช์เปิด/ปิด SSO (Enforce SSO Toggle)`
3. **การ์ดสวิตช์ฉุกเฉิน (Break-Glass Emergency Panel):**
   * กล่องสีเหลือง/แดง พร้อมคำเตือน
   * สวิตช์เปิดโหมด Break-Glass (ต้องพิมพ์ยืนยันเหตุผลก่อนกดยืนยัน)
4. **ปุ่มสั่งซิงก์บัญชีผู้ใช้กับ CIAM ทันที (Mandatory Immediate Sync Button for Mode C):**
   * สำหรับระบบลูกที่เป็น Mode C (เช่น MTPulse): ต้องมีปุ่ม **`[ ⚡ ซิงก์บัญชีผู้ใช้กับ CIAM ทันที ]`** ในแท็บ User Management หรือแท็บ Central IAM
   * เมื่อคลิก ระบบจะส่ง Full Sync ไปยัง CIAM เพื่อตรวจเทียบและนำบัญชีที่ CIAM มอบหมายเพิ่มมาสร้างในเครื่องตนเองทันที รวมถึงปรับสถานะ Active/Inactive ให้ตรงกัน 100% โดยไม่ต้องรอรอบ 120 วินาที

---

### 5.2 มาตรฐานหน้าจอล็อกอินแบบ Responsive: คุ้นเคยเดิมบน Mobile 100% & เลือกได้ยืดหยุ่นบน Desktop (Mobile Familiarity & Desktop Dual-Option)

> [!IMPORTANT]
> **หลักการออกแบบหน้าจอล็อกอินระบบลูก (User-Centric Responsive Login Standard):**  
> จากการใช้งานจริงในองค์กร พนักงานแบ่งออกเป็น 2 กลุ่มอย่างชัดเจน:
> 1. **ผู้ใช้งานผ่าน Mobile (หน้างาน / คลังสินค้า / จัดซื้อ / ฝ่ายผลิต):** มักเข้าใช้งานแอปพลิเคชันนั้นๆ เพียงแอปเดียวบนโทรศัพท์มือถือ **หน้าตา Login ต้องแทบจะเหมือนเดิม 100%** เพื่อไม่ให้พนักงานรู้สึกว่ามีอะไรเปลี่ยนแปลงไปจากเดิมที่เคยใช้งาน
> 2. **ผู้ใช้งานผ่าน Desktop (สำนักงาน / แล็ปท็อป):** มักทำงานหลายระบบพร้อมกัน **ปุ่ม SSO ต้องมีขนาดกะทัดรัด (Compact)** และแสดงควบคู่ไปกับฟอร์มมาตรฐาน เพื่อเปิดโอกาสให้พนักงานเลือกวิธีล็อกอินตามความต้องการได้อย่างอิสระ

---

#### 1. รายละเอียดการแสดงผลแยกตามขนาดหน้าจอ (Responsive Behavior)

| มิติ / หน้าจอ | 📱 เข้าใช้งานด้วย Mobile (จอมือถือ / แท็บเล็ตหน้างาน) | 💻 เข้าใช้งานด้วย Desktop (คอมพิวเตอร์ / แล็ปท็อป) |
| :--- | :--- | :--- |
| **เป้าหมายประสบการณ์ (UX Goal)** | **คงความคุ้นเคยเดิม 100%** ไม่สะดุด ไม่สับสน | **เปิดโอกาสให้เลือก (Freedom of Choice)** รวดเร็วและสะดวก |
| **ฟอร์ม Username & Password** | **แสดงเด่นชัดเป็นฟอร์มหลักทันทีตั้งแต่เปิดหน้าจอ** (ไม่ต้องกดลิงก์ใดๆ เพื่อเปิด) | **แสดงควบคู่กันบนหน้าจอทันที** สามารถกรอกข้อมูลเข้าใช้งานได้ทันที |
| **ปุ่ม Sign In ของระบบเดิม** | เป็นปุ่มหลัก (Primary CTA) สีเด่นชัด ขนาดเต็มแผง | เป็นปุ่มมาตรฐานด้านล่างฟอร์ม |
| **ตำแหน่งและขนาดปุ่ม SSO** | **อยู่ด้านล่างต่อจากฟอร์มหลัก** คั่นด้วยเส้นแบ่ง `— หรือเข้าสู่ระบบด้วย —` ปุ่มขนาดกะทัดรัด (Secondary Option) ไม่แย่งความเด่น | **วางไว้ด้านบนฟอร์มหลัก** คั่นด้วย `— หรือเข้าสู่ระบบด้วยชื่อผู้ใช้งาน —` **ปุ่มขนาดเล็กลง (Compact height `py-2.5`, text-xs/sm)** ไม่ครอบงำหน้าจอ |

---

#### 2. พฤติกรรมตามสถานะระบบ (State-Driven Logic)

##### สถานการณ์ที่ 1: เปิดใช้งาน SSO ปกติ (`ciam_sso_enabled = true` และ `ciam_break_glass_active = false`)
* **บน Desktop:** แสดงปุ่ม SSO ขนาดกะทัดรัด (Compact Button) ด้านบนฟอร์ม คั่นด้วยเส้นแบ่ง `— หรือเข้าสู่ระบบด้วยชื่อผู้ใช้งาน —` ตามด้วยฟอร์ม Username & Password ปกติ
* **บน Mobile:** แสดงฟอร์ม Username & Password ดั้งเดิมเป็นหลัก พร้อมปุ่ม Submit สีเด่นชัด และมีเส้นแบ่ง `— หรือเข้าสู่ระบบด้วย —` พร้อมปุ่ม SSO ขนาดย่อมด้านล่างสุด
* **True SSO:** เมื่อกดปุ่ม SSO หากมีเซสชันเดิมบน Central IAM ระบบจะ Redirect แลก Token และเข้าสู่ระบบทันทีภายใน ~0.8 วินาที

##### สถานการณ์ที่ 2: ปิดใช้งาน SSO ในระบบลูก (`ciam_sso_enabled = false`)
* ❌ **ซ่อนปุ่ม SSO และเส้นแบ่งทั้งหมด 100%:** ไม่ต้องเรนเดอร์ปุ่ม SSO และไม่ต้องมีเส้นคั่นใดๆ ทั้งบน Desktop และ Mobile
* ❌ **ห้ามแสดงข้อความเตือนหรือคำว่า "สำรอง":** ห้ามขึ้นว่า "SSO Disabled" หรือ "เข้าสู่ระบบสำรอง"
* **ผลลัพธ์:** หน้าจอจะกลายเป็นฟอร์ม Login ดั้งเดิมของระบบลูก 100%

##### สถานการณ์ที่ 3: โหมดฉุกเฉิน Break-Glass (`ciam_break_glass_active = true`)
* แสดงกล่องแจ้งเตือนสีส้ม/เหลืองด้านบน: `⚠️ ระบบอยู่ในโหมดฉุกเฉิน (Break-Glass Active) - กรุณาเข้าใช้งานด้วยรหัสผ่านตรง`
* ซ่อนปุ่ม SSO และให้พนักงานล็อกอินผ่านฟอร์ม Username / Password ดั้งเดิมตรงไปยังระบบหรือ AD Gateway

---

#### 3. ตัวอย่างโค้ดมาตรฐานสำหรับ Dev ระบบลูก (React / Next.js + Tailwind CSS)

ทีมพัฒนาของแต่ละ Spoke สามารถนำโครงสร้าง JSX และ Tailwind Responsive Classes (`hidden md:block` และ `block md:hidden`) ไปปรับใช้ได้ทันที:

```tsx
export default function SpokeLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [ssoConfig, setSsoConfig] = useState({ sso_enabled: true, break_glass_active: false });

  return (
    <div className="w-full max-w-md bg-slate-900 rounded-2xl p-6 sm:p-8 border border-slate-800">
      {/* 1. Header & Logo ระบบลูก */}
      <div className="text-center mb-6">
        <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-white">
          APP
        </div>
        <h1 className="text-xl font-bold text-white">ชื่อระบบงาน (Spoke App)</h1>
        <p className="text-xs text-slate-400 mt-1">คำอธิบายระบบงาน</p>
      </div>

      {/* 2. Desktop SSO Button: ขนาดย่อมลงมา (Compact) อยู่ด้านบนสำหรับ Desktop */}
      {ssoConfig?.sso_enabled && !ssoConfig.break_glass_active && (
        <div className="hidden md:block mb-5">
          <button
            type="button"
            onClick={handleCiamSso}
            className="w-full py-2.5 px-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-xs rounded-xl shadow-md flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <span>🛡️ เข้าสู่ระบบด้วย Window Asia SSO ✨</span>
          </button>
          
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800" />
            </div>
            <div className="relative flex justify-center text-[11px]">
              <span className="bg-slate-900 px-3 text-slate-500">หรือเข้าสู่ระบบด้วยชื่อผู้ใช้งาน</span>
            </div>
          </div>
        </div>
      )}

      {/* 3. Standard Login Form: แสดงเด่นชัดเสมอ ทั้งบน Mobile และ Desktop */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">ชื่อผู้ใช้งาน (Username)</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="ชื่อผู้ใช้งาน AD หรือ Local"
            className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">รหัสผ่าน (Password)</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="กรอกรหัสผ่าน"
            className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* ปุ่มเข้าสู่ระบบหลัก (Primary CTA) */}
        <button
          type="submit"
          className="w-full mt-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl shadow-md transition cursor-pointer"
        >
          เข้าสู่ระบบ (Sign In)
        </button>
      </form>

      {/* 4. Mobile Secondary SSO: อยู่ด้านล่างฟอร์มหลักในขนาดกะทัดรัด สำหรับจอมือถือ */}
      {ssoConfig?.sso_enabled && !ssoConfig.break_glass_active && (
        <div className="block md:hidden pt-4 mt-1">
          <div className="relative mb-3">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800" />
            </div>
            <div className="relative flex justify-center text-[10px]">
              <span className="bg-slate-900 px-2.5 text-slate-500">หรือเข้าสู่ระบบด้วย</span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleCiamSso}
            className="w-full py-2.5 px-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white text-xs rounded-xl flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <span>🛡️ Window Asia SSO ✨</span>
          </button>
        </div>
      )}
    </div>
  );
}
```

---

### 5.3 มาตรฐานการออกจากระบบและการหมดอายุของเซสชัน (Seamless Logout & Expired Lifecycle)

เพื่อให้ประสบการณ์การทำงานข้ามระบบของพนักงาน (Cross-App Experience) เป็นไปอย่างไร้รอยต่อตามหลักการ Enterprise Launchpad:

1. **เมื่อพนักงานกด "ออกจากระบบ (Logout)" ในระบบลูก:**
   * **กรณีล็อกอินผ่าน SSO (พนักงาน 99%):**
     * ระบบลูกทำการล้าง Token และ Session เฉพาะของระบบลูกเอง
     * นำทางผู้ใช้กลับไปยังหน้า **Central IAM Portal (`https://ciam.windowasia.com/portal`)** ทันที
     * **ผลลัพธ์:** พนักงานกลับมาที่หน้าโต๊ะทำงานกลาง โดยที่เซสชันของ Central IAM ยังคงอยู่ ทำให้สามารถคลิกเปิดระบบงานอื่น (เช่น SAP B1, QMS, QOL, HR) ต่อได้ทันทีโดยไม่ต้องล็อกอินใหม่
   * **กรณีล็อกอินผ่าน Local Admin (`admin` กรณีฉุกเฉิน):**
     * นำทางกลับไปยังหน้า `/login` ของระบบลูกตามเดิม
2. **เมื่อเซสชันในระบบลูกหมดอายุ (HTTP 401 Unauthorized):**
   * หาก Request ในระบบลูกได้รับ HTTP 401 (Token Expired):
     * ให้ล้าง Token ของระบบลูก และนำทางผู้ใช้กลับไปยัง Central IAM Portal (`https://ciam.windowasia.com/portal`) เช่นเดียวกัน
     * หากเซสชันบน Central IAM ยังไม่หมดอายุ พนักงานสามารถคลิกเปิดระบบลูกใหม่ได้ทันทีใน 1 วินาที (Seamless Re-auth) โดยงานไม่สะดุด

---

## 6. ลำดับขั้นตอนการพัฒนาสำหรับทีม Dev (Step-by-Step Implementation Checklist)

1. [ ] **สร้างตารางและ Seed ข้อมูล:** ตรวจสอบตาราง `system_settings` และใส่ Seed Keys สำหรับหมวด `central_iam`
2. [ ] **ปรับปรุง Service Config:** เปลี่ยน `get_sso_client()` ให้อ่านค่าจากตาราง `system_settings` (ไม่ใช่จากไฟล์ `.env`)
3. [ ] **สร้าง API Channel หมวด A (Settings):** พัฒนา Endpoint `GET`, `PUT`, และ `POST /test-connection` สำหรับ System Settings
4. [ ] **เชื่อมโยงการบันทึก Audit Logs:** ติดตั้งคำสั่ง `record_transaction_log` ตาม Event Code ทั้ง 7 เคส ในตารางข้อ 4
5. [ ] **ทดสอบบน VPS:** 
   * เข้าหน้า System Settings บนแอปพลิเคชัน
   * ระบุ `ciam_base_url` และกดปุ่มทดสอบการเชื่อมต่อ
   * ตรวจสอบว่าหน้า Login แสดงปุ่ม *"เข้าสู่ระบบด้วย Central IAM (SSO)"*
   * ทดสอบคลิกเข้าใช้งานจริง และตรวจสอบตาราง `transaction_logs` ว่ามีข้อมูลครบถ้วน

---

## 7. มาตรฐานการซิงก์ข้อมูลอัตโนมัติประจำวัน (Daily Scheduled Sync & Manual Trigger)

เพื่อให้ข้อมูลสถานะบัญชีพนักงานและเวลาใช้งานล่าสุดข้ามระบบ (Cross-System Activity) มีความแม่นยำสูงสุด Central IAM ได้กำหนดมาตรฐานรอบการซิงก์ข้อมูลดังนี้:

1. **รอบการซิงก์อัตโนมัติ (Automated Daily Schedule):**
   * ระบบ Central IAM จะเริ่มกระบวนการซิงก์ข้อมูลรอบประจำวันทุกวันเวลา **04:00 AM (เวลาไทย Asia/Bangkok, GMT+7)**
   * เป็นช่วงเวลาที่มีปริมาณการใช้งานระบบต่ำ (Off-Peak Hours) ป้องกันผลกระทบต่อภาระการทำงานของเซิร์ฟเวอร์ (Server Load)
   * ข้อมูลสรุปสถานะการเข้าใช้งานและบัญชีคงค้างจะพร้อมแสดงผลบน Dashboard ให้ฝ่ายบุคคล (HR) และผู้บริหารก่อนเวลาเริ่มงาน 08:00 น.
2. **การสั่งซิงก์ด้วยตนเอง (On-Demand Manual Sync):**
   * **ปุ่มซิงก์แยกตามระบบ (Per-App Sync):** อยู่ที่การ์ดของแต่ละระบบ สามารถกดเพื่อตรวจสอบสถานะของระบบใดระบบหนึ่งได้ทันที
   * **ปุ่มซิงก์ทุกระบบพร้อมกัน (Sync All):** ปุ่ม `[ ⚡ ซิงก์ทุกระบบทันที ]` ที่ส่วนหัวของหน้า Applications สำหรับผู้ดูแลระบบที่ต้องการให้ทุก Spoke อัปเดตข้อมูลพร้อมกันในทันที
3. **การตั้งค่ากำหนดเวลา (Customizable Schedule):**
   * ผู้ดูแลระบบสามารถปรับเปลี่ยนเวลาซิงก์ หรือเปิด/ปิดระบบ Auto-Sync ได้ผ่านหน้าต่าง **"กำหนดเวลาซิงก์อัตโนมัติ"** บนหน้าเว็บ Central IAM

---

## 8. นโยบายการตรวจสอบ Active Directory (AD Read-Only Audit Policy)

เพื่อให้เป็นไปตามมาตรฐานความปลอดภัยข้อมูลสารสนเทศ (ISO 27001 / Zero Trust Architecture) และหลักการจำกัดสิทธิ์ขั้นต่ำ (Principle of Least Privilege):

1. **บทบาทการทำงานแบบ Read-Only Audit:**
   * การเชื่อมต่อของ Central IAM ไปยัง Active Directory Domain Services (AD DS) กำหนดให้ใช้สิทธิ์ระดับ **อ่านอย่างเดียว (Read-Only)**
   * Central IAM จะดึงเฉพาะรายชื่อพนักงาน (`sAMAccountName`, `displayName`, `mail`, `department`, `employeeID`) และตรวจสอบสถานะ Flag `userAccountControl` (512 = Enabled, 514 = Disabled)
2. **การไม่แตะต้อง Domain Controller (Zero-Risk Operations):**
   * Central IAM **ไม่มีความจำเป็นและไม่ได้รับอนุญาตให้ส่งคำสั่งแก้ไขหรือ Disable บัญชีบน AD Domain Controller โดยตรง**
   * ขั้นตอนการระงับหรือปิดบัญชีบน AD ยังคงเป็นหน้าที่ตามขั้นตอนทางการของ IT Helpdesk / ฝ่ายบุคคล (HR)
3. **การตัดสิทธิ์เฉพาะระบบลูก (Targeted Spoke Deprovisioning):**
   * หน้าที่สำคัญของ Central IAM คือการเป็น **Governance & Reconciliation Hub**
   * เมื่อตรวจพบว่าบัญชีบน AD ถูกปิดใช้งาน (`userAccountControl` = 514) แต่ในระบบลูก (เช่น IRM, QOL, SAP B1) ยังเปิดค้างอยู่ ระบบจะระบุเป็น **"บัญชีผี (Discrepancy)"** และส่งคำสั่งระงับสิทธิ์ (Deprovision) ไปยังระบบลูกเป้าหมายเพื่อปิดความเสี่ยงทันที โดยไม่รบกวน AD DC

---

## 9. สรุปความสัมพันธ์ด้านการยืนยันตัวตนกับ Active Directory (AD Authentication Clarification)

> [!NOTE]
> **คำถามพบบ่อย: ทำไมนักพัฒนาระบบลูกถึงไม่ต้องเชื่อมต่อกับ Active Directory / LDAP โดยตรง?**
> 
> ในสถาปัตยกรรม Central IAM บริษัท วินโดว์ เอเชีย จำกัด (มหาชน):
> 1. **Central IAM ทำหน้าที่เป็น Identity Provider (IdP) กลางเพียงจุดเดียว:**
>    * เมื่อผู้ใช้คลิก *"เข้าสู่ระบบด้วย Central IAM (SSO)"* ระบบลูกจะ Redirect ผู้ใช้มายังหน้าล็อกอินของ Central IAM
>    * Central IAM จะทำการตรวจสอบชื่อผู้ใช้และรหัสผ่านกับ Domain Controller (ผ่าน AD Proxy Service ภายใน) โดยตรง
> 2. **ความปลอดภัยระดับสูงสุด (Zero Domain Exposure):**
>    * ระบบลูก **ไม่ต้องเปิด Port 389/636 (LDAP) ข้ามเครือข่าย**
>    * ระบบลูก **ไม่ต้องเก็บ Service Account หรือรหัสผ่านของ Domain Controller ไว้ในซอร์สโค้ด**
>    * ระบบลูกเพียงแค่รอรับ JWT Token (RS256) ที่ผ่านการพิสูจน์ตัวตนจาก AD แล้วเท่านั้น
> 3. **โหมดสำรองฉุกเฉิน (Break-Glass Mode):**
>    * เฉพาะในกรณีที่ระบบคลาวด์หรือเน็ตเวิร์กของ Central IAM ขัดข้อง ระบบลูกสามารถเปิดใช้งาน `ciam_break_glass_active = true` เพื่อสลับไปยืนยันตัวตนตรงกับ Local AD Gateway (`http://172.18.0.1:3100`) ผ่าน API ได้ทันที

---

## 10. โค้ดตัวอย่างพร้อมใช้งานสำหรับทีม Developer (Implementation Boilerplate)

### 10.1 ตัวอย่าง Python (FastAPI): Group C Inbound Directory & Governance Channel (ตามมาตรฐาน IRM)

```python
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException, Depends, Request, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/directory", tags=["Central Management"])

# ดึงค่า M2M Key จากตาราง system_settings (key: ciam_m2m_key) หรือค่าคงที่
EXPECTED_M2M_KEY = "sec_your_app_mgmt_key_here"
ALLOWED_CIAM_IP = "157.173.219.153" # IP ของเซิร์ฟเวอร์ Central IAM

def verify_ciam_management_access(
    request: Request,
    x_management_api_key: Optional[str] = Header(None, alias="X-Management-API-Key"),
):
    # 1. ตรวจสอบ M2M API Key
    if not x_management_api_key or x_management_api_key != EXPECTED_M2M_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Management-API-Key header.",
        )
    # 2. ตรวจสอบ IP Whitelist (ถ้าต้องการจำกัดระดับ Network)
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    # ใน Local/Dev ให้ยกเว้น localhost
    if client_ip not in [ALLOWED_CIAM_IP, "127.0.0.1", "localhost", "::1"]:
        # raise HTTPException(status_code=403, detail=f"IP {client_ip} not allowed")
        pass
    return {"client_ip": client_ip}

class CreateAccountRequest(BaseModel):
    username: str
    full_name: str
    email: Optional[str] = None
    department: Optional[str] = None
    group_name: Optional[str] = None
    use_ad_auth: bool = True
    created_by: Optional[str] = "Central-IAM-Service"

class UpdateStatusRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = "Status updated via Central Management API"
    updated_by: Optional[str] = "Central-IAM-Service"

@router.get("/accounts", dependencies=[Depends(verify_ciam_management_access)])
def list_accounts_for_ciam(status: str = "all", department: Optional[str] = None, search: Optional[str] = None):
    """ใช้ทั้ง Ping/Health Check และ Reconciliation ประจำวันเวลา 04:00 น."""
    # TODO: Query จากตาราง users ในฐานข้อมูลของระบบลูก
    return {
        "application_name": "My Spoke Application",
        "total_accounts": 1,
        "active_accounts": 1,
        "inactive_accounts": 0,
        "accounts": [
            {
                "id": 1,
                "username": "somchai.p",
                "full_name": "นายสมชาย พร้อมพงษ์",
                "email": "somchai.p@windowasia.com",
                "department": "Purchasing",
                "group_name": "PU User",
                "use_ad_auth": True,
                "is_active": True,
                "last_login_at": "2026-09-30T08:30:00Z",
                "created_at": "2026-09-20T10:00:00Z",
                "updated_at": "2026-09-30T08:30:00Z"
            }
        ]
    }

@router.post("/accounts", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_ciam_management_access)])
def create_account_from_ciam(payload: CreateAccountRequest):
    """สร้างหรือ Provision บัญชีผู้ใช้ใหม่จาก Central IAM"""
    # TODO: ตรวจสอบว่ามีอยู่แล้วหรือไม่ ถ้ามีให้ raise HTTPException(409, detail="User exists")
    # TODO: สร้าง User ใหม่ และบันทึกลงฐานข้อมูล
    return {
        "success": True,
        "id": 99,
        "username": payload.username,
        "message": f"Account '{payload.username}' created successfully.",
        "group_name": payload.group_name,
        "is_active": True,
        "created_at": datetime.now()
    }

@router.patch("/accounts/{username}/status", dependencies=[Depends(verify_ciam_management_access)])
def update_account_status_from_ciam(username: str, payload: UpdateStatusRequest):
    """1-Click Offboarding (ระงับสิทธิ์ทันที) หรือ คืนสิทธิ์การใช้งาน"""
    # TODO: อัปเดต user.is_active = payload.is_active
    # TODO: ถ้า payload.is_active == False ให้เตะ Session และ Revoke Refresh Tokens ทั้งหมดทันที
    return {
        "username": username,
        "is_active": payload.is_active,
        "message": f"Status for '{username}' updated successfully.",
        "updated_at": datetime.now()
    }
```

### 10.2 ตัวอย่าง Node.js (Express.js): Group C Inbound Directory Channel

```javascript
const express = require('express');
const router = express.Router();

const EXPECTED_M2M_KEY = process.env.CIAM_M2M_KEY || "sec_your_app_mgmt_key_here";
const ALLOWED_CIAM_IP = "157.173.219.153";

// Middleware ตรวจสอบความปลอดภัย
function verifyCiamManagementAccess(req, res, next) {
  const apiKey = req.headers['x-management-api-key'];
  if (!apiKey || apiKey !== EXPECTED_M2M_KEY) {
    return res.status(401).json({ status: "FAILED", message: "Invalid or missing X-Management-API-Key" });
  }
  next();
}

// 1. Directory Inventory & Health Check
router.get('/api/v1/directory/accounts', verifyCiamManagementAccess, async (req, res) => {
  // TODO: Query users จากฐานข้อมูล
  res.json({
    application_name: "Node Spoke App",
    total_accounts: 1,
    active_accounts: 1,
    inactive_accounts: 0,
    accounts: [
      {
        id: 1,
        username: "somchai.p",
        full_name: "นายสมชาย พร้อมพงษ์",
        email: "somchai.p@windowasia.com",
        department: "Purchasing",
        group_name: "Standard User",
        use_ad_auth: true,
        is_active: true,
        created_at: new Date()
      }
    ]
  });
});

// 2. Remote User Provisioning
router.post('/api/v1/directory/accounts', verifyCiamManagementAccess, async (req, res) => {
  const { username, full_name, email, department, group_name, use_ad_auth } = req.body;
  // TODO: Insert user หรือตอบกลับ 409 Conflict หากมีอยู่แล้ว
  res.status(201).json({
    success: true,
    id: 100,
    username,
    message: `Account '${username}' provisioned successfully`,
    is_active: true,
    created_at: new Date()
  });
});

// 3. 1-Click Offboarding & Reactivate
router.patch('/api/v1/directory/accounts/:username/status', verifyCiamManagementAccess, async (req, res) => {
  const { username } = req.params;
  const { is_active, reason } = req.body;
  // TODO: อัปเดต is_active และถ้า false ให้เตะ Session ออกจากระบบทันที
  res.json({
    username,
    is_active,
    message: `Account status updated to ${is_active}`,
    updated_at: new Date()
  });
});

module.exports = router;
```

---

### 10.3 ตัวอย่างการทำ SSO Client ฝั่งระบบลูก (Python FastAPI / Backend)

ตัวอย่างโค้ดที่ระบบลูกนำไปใช้สำหรับ:
1. สร้าง PKCE และส่ง User ไปหน้า Login ของ Central IAM
2. รับ Callback แลก Token และตรวจสอบสิทธิ์พนักงานจาก Active Directory

```python
import hashlib
import base64
import secrets
import httpx
import jwt # pip install pyjwt cryptography
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth/sso", tags=["SSO Client"])

CIAM_BASE_URL = "https://ciam.windowasia.com"
CLIENT_ID = "irm-spoke-client"                  # ดึงจาก system_settings
CLIENT_SECRET = "sec_irm_oauth_secret_2026"     # ดึงจาก system_settings
REDIRECT_URI = "https://irm.windowasia.com/auth/callback"

# เก็บ code_verifier ชั่วคราว (ใน Production ควรเก็บใน Redis หรือ Encrypted Session Cookie)
pkce_sessions = {}

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').replace('=', '')

@router.get("/login")
def sso_login():
    """Step 1: สร้าง PKCE S256 Challenge และ Redirect ผู้ใช้ไปที่ Central IAM"""
    # 1. สร้าง Code Verifier & Challenge
    verifier = base64url_encode(secrets.token_bytes(32))
    challenge = base64url_encode(hashlib.sha256(verifier.encode('utf-8')).digest())
    state = secrets.token_hex(16)

    pkce_sessions[state] = verifier

    # 2. สร้าง Authorize URL
    auth_url = (
        f"{CIAM_BASE_URL}/oauth/authorize?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=openid+profile+email&"
        f"state={state}&"
        f"code_challenge={challenge}&"
        f"code_challenge_method=S256"
    )
    return RedirectResponse(url=auth_url)

class CallbackPayload(BaseModel):
    code: str
    state: Optional[str] = None
    code_verifier: Optional[str] = None
    redirect_uri: Optional[str] = None

@router.post("/callback")
async def sso_callback(payload: CallbackPayload, db: Session = Depends(get_db)):
    """Step 2: รับ Code จาก Central IAM แลกเปลี่ยน Token และดึง Claims จาก AD (รองรับทั้ง Spoke-Initiated และ Portal Launch)"""
    # 0. ตรวจสอบว่าระบบลูกเปิดใช้งาน SSO อยู่หรือไม่ (Break-Glass Active Guard)
    sso_cfg = get_spoke_sso_settings(db)
    if not sso_cfg.get("sso_enabled", True) or sso_cfg.get("break_glass_active", False):
        raise HTTPException(
            status_code=503,
            detail="Single Sign-On is currently disabled on this application (Break-Glass Mode Active)."
        )

    # ดึง code_verifier: ใช้จาก payload ก่อน ถ้าไม่มีจึงลองดึงจาก pkce_sessions (ถ้ามาจาก Portal verifier จะเป็น None ซึ่งอนุญาตให้ผ่านได้)
    verifier = payload.code_verifier or (pkce_sessions.pop(payload.state, None) if payload.state else None)

    # 1. แลก Authorization Code เป็น Tokens กับ Central IAM (Backend-to-Backend)
    token_request_data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": payload.code,
        "redirect_uri": payload.redirect_uri or REDIRECT_URI,
    }
    # แนบ code_verifier เฉพาะเมื่อมีค่า (กรณี Spoke-Initiated PKCE)
    if verifier:
        token_request_data["code_verifier"] = verifier

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_res = await client.post(
            f"{CIAM_BASE_URL}/api/v1/oauth/token",
            data=token_request_data
        )

        if token_res.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Token exchange failed: {token_res.text}")

        token_data = token_res.json()
        id_token = token_data.get("id_token")

        # 2. ดึง JWKS Public Keys เพื่อตรวจสอบ Asymmetric Signature (RS256)
        jwks_res = await client.get(f"{CIAM_BASE_URL}/.well-known/jwks.json")
        jwks = jwks_res.json()

    # 3. ตรวจสอบ Signature และอ่าน Claims จาก AD
    jwks_client = jwt.PyJWKClient(f"{CIAM_BASE_URL}/.well-known/jwks.json")
    signing_key = jwks_client.get_signing_key_from_jwt(id_token)

    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        issuer=CIAM_BASE_URL
    )

    # 4. ข้อมูลพนักงานที่ผ่านการตรวจสอบจาก Active Directory เรียบร้อยแล้ว:
    username = claims.get("preferred_username") # sAMAccountName เช่น somchai.p
    full_name = claims.get("name")              # ชื่อ-นามสกุล เช่น นายสมชาย พร้อมพงษ์
    email = claims.get("email")                 # อีเมลบริษัท
    department = claims.get("department")       # แผนก เช่น Purchasing
    employee_id = claims.get("employee_id")     # รหัสพนักงาน เช่น WA-1029
    groups = claims.get("groups", [])           # AD Security Groups

    # 5. ออก Session หรือ JWT ของระบบลูก และอนุญาตให้เข้าใช้งาน Dashboard ได้ทันที
    return {
        "status": "success",
        "message": f"เข้าสู่ระบบสำเร็จ ยินดีต้อนรับ {full_name}",
        "user": {
            "username": username,
            "full_name": full_name,
            "email": email,
            "department": department,
            "employee_id": employee_id,
            "groups": groups
        },
        "spoke_token": "your_app_session_jwt_token_here"
    }
```

---

### 10.4 ตัวอย่างการทำ SSO Client ฝั่งระบบลูก (Node.js / Express / Next.js)

```javascript
const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const jwt = require('jsonwebtoken');
const jwksClient = require('jwks-rsa');

const router = express.Router();

const CIAM_BASE_URL = "https://ciam.windowasia.com";
const CLIENT_ID = "irm-spoke-client";
const CLIENT_SECRET = "sec_irm_oauth_secret_2026";
const REDIRECT_URI = "https://irm.windowasia.com/auth/callback";

// JWKS Client สำหรับดึง Public Key ของ CIAM
const jwks = jwksClient({
  jwksUri: `${CIAM_BASE_URL}/.well-known/jwks.json`,
  cache: true,
  rateLimit: true
});

function getKey(header, callback) {
  jwks.getSigningKey(header.kid, function (err, key) {
    const signingKey = key?.publicKey || key?.rsaPublicKey;
    callback(null, signingKey);
  });
}

function base64url(buffer) {
  return buffer.toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

// 1. Endpoint ส่ง User ไปล็อกอินที่ Central IAM
router.get('/login', (req, res) => {
  const verifier = base64url(crypto.randomBytes(32));
  const challenge = base64url(crypto.createHash('sha256').update(verifier).digest());
  const state = crypto.randomBytes(16).toString('hex');

  // บันทึก verifier ใน Session หรือ Cookie
  res.cookie('sso_verifier', verifier, { httpOnly: true, secure: true, maxAge: 300000 });

  const authUrl = `${CIAM_BASE_URL}/oauth/authorize?response_type=code` +
    `&client_id=${encodeURIComponent(CLIENT_ID)}` +
    `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}` +
    `&scope=openid+profile+email` +
    `&state=${state}` +
    `&code_challenge=${challenge}` +
    `&code_challenge_method=S256`;

  res.redirect(authUrl);
});

// 2. Endpoint รับ Callback และดึงข้อมูลพนักงานจาก AD (รองรับทั้ง Spoke-Initiated และ Portal Launch)
router.post('/callback', async (req, res) => {
  const { code, code_verifier } = req.body;
  const verifier = code_verifier || req.cookies['sso_verifier'];

  try {
    // 2.1 แลก Authorization Code เป็น Tokens
    const tokenPayload = {
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      code: code,
      redirect_uri: REDIRECT_URI,
    };
    if (verifier) {
      tokenPayload.code_verifier = verifier;
    }

    const tokenRes = await axios.post(
      `${CIAM_BASE_URL}/api/v1/oauth/token`,
      new URLSearchParams(tokenPayload).toString(),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );

    const { id_token } = tokenRes.data;

    // 2.2 ตรวจสอบ Signature ของ ID Token ด้วย JWKS
    jwt.verify(id_token, getKey, {
      algorithms: ['RS256'],
      audience: CLIENT_ID,
      issuer: CIAM_BASE_URL
    }, (err, claims) => {
      if (err) {
        return res.status(401).json({ status: "FAILED", message: "Invalid ID Token Signature" });
      }

      // 2.3 อ่านข้อมูลพนักงานจาก AD
      const { preferred_username, name, email, department, employee_id, groups } = claims;

      // TODO: ออก Session Token ของระบบลูก และส่งกลับให้ Frontend
      res.json({
        status: "SUCCESS",
        user: { username: preferred_username, name, email, department, employee_id, groups }
      });
    });
  } catch (error) {
    res.status(500).json({ status: "FAILED", message: error.response?.data || error.message });
  }
});

module.exports = router;
```

---

### 10.5 ตัวอย่างหน้า Frontend Callback มาตรฐาน (Next.js 14 / React App Router)
ทีมพัฒนา Frontend สามารถนำโค้ดนี้ไปวางที่ `src/app/auth/callback/page.tsx` ได้ทันที ซึ่งถูกออกแบบให้รองรับทั้งการกด SSO จากหน้า Login ของระบบลูกเอง และการกดเปิดผ่าน Central IAM Employee Portal โดยไม่เกิดปัญหา *"SSO session ไม่ถูกต้องหรือหมดอายุ"*:

```tsx
'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

export default function SsoCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [statusText, setStatusText] = useState('กำลังยืนยันตัวตนกับ Central IAM...');
  const [error, setError] = useState<string | null>(null);
  const executedRef = useRef(false);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (!code) {
      setError('ไม่พบ Authorization Code ใน URL Redirect จาก Central IAM');
      return;
    }

    // ป้องกันการยิง API ซ้ำ 2 รอบใน React StrictMode
    if (executedRef.current) return;
    executedRef.current = true;

    const exchangeToken = async () => {
      try {
        // ดึง code_verifier และ state จาก sessionStorage (ถ้าเปิดมาจาก Portal ค่านี้จะว่าง)
        const codeVerifier = sessionStorage.getItem('sso_code_verifier') || '';
        const savedState = sessionStorage.getItem('sso_state');

        // หาก state ไม่ตรงกับที่เซฟไว้ ให้เตือนใน Console พอ ห้ามบล็อกการเข้าสู่ระบบ
        if (savedState && state && savedState !== state) {
          console.warn('SSO state mismatch warning (Continuing for Portal Launch compatibility)');
        }

        setStatusText('กำลังแลกเปลี่ยนรหัสและยืนยัน Asymmetric RS256 Signature...');

        const redirectUri = window.location.origin + '/auth/callback';
        const res = await fetch('/api/auth/sso/callback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code,
            code_verifier: codeVerifier,
            redirect_uri: redirectUri,
            state: state || undefined,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'การยืนยันตัวตนกับระบบลูกล้มเหลว');
        }

        const data = await res.json();

        // ล้าง sessionStorage
        sessionStorage.removeItem('sso_code_verifier');
        sessionStorage.removeItem('sso_state');

        setStatusText('ยืนยันตัวตนสำเร็จ! กำลังนำเข้าสู่ระบบ...');

        // บันทึก Session Token ของระบบลูก และพาเข้าหน้าหลัก
        localStorage.setItem('access_token', data.access_token);
        router.push('/');
      } catch (err: any) {
        console.error('SSO Callback error:', err);
        setError(err.message || 'เกิดข้อผิดพลาดในการยืนยันตัวตน');
      }
    };

    exchangeToken();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-slate-900 text-white">
        <div className="max-w-md w-full bg-slate-800 p-6 rounded-2xl border border-rose-500/30 text-center space-y-4">
          <div className="text-rose-400 font-bold text-lg">เข้าสู่ระบบไม่สำเร็จ</div>
          <p className="text-xs text-slate-300">{error}</p>
          <button
            onClick={() => router.push('/login')}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg cursor-pointer transition"
          >
            กลับสู่หน้าเข้าสู่ระบบ
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-900 text-white">
      <div className="text-center space-y-3">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs text-slate-400">{statusText}</p>
      </div>
    </div>
  );
}
```

---

### 10.6 ตัวอย่างการจัดการ Logout และ 401 Session Expired บน Frontend (React / Next.js / Vue)

ตัวอย่างโค้ดฝั่ง Client ของระบบลูกที่ช่วยให้รองรับ Seamless Return to Portal:

```typescript
// 1. ฟังก์ชัน Logout ในระบบลูก (เช่น ใน Header หรือ User Menu)
export const handleLogout = () => {
  const authProvider = typeof window !== 'undefined' ? localStorage.getItem('app_auth_provider') : null;
  const ciamPortalUrl =
    (typeof window !== 'undefined' && localStorage.getItem('app_ciam_portal_url')) ||
    'https://ciam.windowasia.com/portal';

  // ล้าง Token เฉพาะของระบบลูก
  if (typeof window !== 'undefined') {
    localStorage.removeItem('app_access_token');
    localStorage.removeItem('app_refresh_token');
    localStorage.removeItem('app_auth_provider');
  }

  if (authProvider === 'local') {
    // ผู้ใช้ที่เป็น Local Admin -> เด้งไปหน้า Login ของระบบลูก
    window.location.href = '/login';
  } else {
    // ผู้ใช้ที่เข้าผ่าน SSO -> นำทางกลับสู่ Central IAM Portal กลางอย่างไร้รอยต่อ
    window.location.href = ciamPortalUrl;
  }
};

// 2. การดักจับ HTTP 401 (Session Expired Interceptor ใน Axios หรือ Fetch)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      const isLoginPage = window.location.pathname === '/login';
      const isAuthCallback = window.location.pathname === '/auth/callback';
      if (!isLoginPage && !isAuthCallback) {
        handleLogout();
      }
    }
    return Promise.reject(error);
  }
);
```
