// MOAMOA administrator API.
// Required custom Edge Function secret: MOAMOA_ADMIN_EMAILS (comma-separated exact email allowlist).
// Supabase project keys are read from current key dictionaries, with legacy fallbacks.
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};

const reply = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: corsHeaders });

Deno.serve(async (req) => {
  let adminClient: ReturnType<typeof createClient> | null = null;
  let currentAction = "unknown";
  let actorEmail = "";
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return reply({ error: "Method not allowed" }, 405);

  try {
    const authHeader = req.headers.get("Authorization") || "";
    if (!authHeader.startsWith("Bearer ")) return reply({ error: "로그인이 필요합니다." }, 401);

    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const publishableKeys = JSON.parse(Deno.env.get("SUPABASE_PUBLISHABLE_KEYS") || "{}");
    const secretKeys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}");
    const anonKey = publishableKeys.default || Deno.env.get("SUPABASE_ANON_KEY");
    const serviceRoleKey = secretKeys.default || Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    const allowlist = (Deno.env.get("MOAMOA_ADMIN_EMAILS") || "")
      .split(",").map((v) => v.trim().toLowerCase()).filter(Boolean);
    if (!supabaseUrl || !anonKey || !serviceRoleKey || allowlist.length === 0) {
      return reply({ error: "관리자 API 서버 설정이 완료되지 않았습니다." }, 500);
    }

    const token = authHeader.slice("Bearer ".length);
    const userClient = createClient(supabaseUrl, anonKey, {
      global: { headers: { Authorization: `Bearer ${token}` } },
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data: { user }, error: userError } = await userClient.auth.getUser(token);
    if (userError || !user?.email) return reply({ error: "로그인이 만료되었습니다." }, 401);
    if (!allowlist.includes(user.email.toLowerCase())) return reply({ error: "관리자 권한이 없습니다." }, 403);
    actorEmail = user.email;

    const admin = createClient(supabaseUrl, serviceRoleKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    adminClient = admin;
    const body = await req.json();
    const action = String(body.action || "");
    currentAction = action;
    const audit = async (event: string, userId: string | null = null, details: Record<string, unknown> = {}) => {
      const { error } = await admin.from("member_activity_logs").insert({
        user_id: userId, email: actorEmail, action: event,
        details: { actor: "admin", ...details },
      });
      if (error) console.error("MOAMOA audit log write failed:", error.message);
    };

    if (action === "list_announcements") {
      const { data, error } = await admin.from("announcements")
        .select("id,title,body,is_published,created_at,updated_at,published_at")
        .order("created_at", { ascending: false }).limit(200);
      if (error) throw error;
      return reply({ announcements: data || [] });
    }

    if (action === "save_announcement") {
      const id = String(body.id || "");
      const title = String(body.title || "").trim();
      const content = String(body.body || "").trim();
      const isPublished = body.is_published === true;
      if (!title || title.length > 120 || !content || content.length > 10000) {
        return reply({ error: "제목은 1~120자, 내용은 1~10,000자로 입력해 주세요." }, 400);
      }
      const values = {
        title, body: content, is_published: isPublished,
        updated_at: new Date().toISOString(),
        published_at: isPublished ? new Date().toISOString() : null,
      };
      const result = id
        ? await admin.from("announcements").update(values).eq("id", id).select("id").single()
        : await admin.from("announcements").insert(values).select("id").single();
      if (result.error) throw result.error;
      await audit(id ? "공지사항 수정" : "공지사항 등록", null, { announcement_id: result.data.id, title });
      return reply({ saved: true, id: result.data.id });
    }

    if (action === "delete_announcement") {
      const id = String(body.id || "");
      if (!id) return reply({ error: "공지사항 ID가 필요합니다." }, 400);
      const { error } = await admin.from("announcements").delete().eq("id", id);
      if (error) throw error;
      await audit("공지사항 삭제", null, { announcement_id: id });
      return reply({ deleted: true });
    }

    if (action === "list_activity_logs") {
      const { data, error } = await admin.from("member_activity_logs")
        .select("id,user_id,email,action,details,created_at")
        .order("created_at", { ascending: false }).limit(200);
      if (error) throw error;
      return reply({ logs: data || [] });
    }

    if (action === "report_error") {
      const message = String(body.message || "").trim();
      const source = String(body.source || "manager").slice(0, 120);
      if (!message) return reply({ error: "오류 내용이 필요합니다." }, 400);
      const { error } = await admin.from("admin_error_logs").insert({
        source, message: message.slice(0, 1500),
        details: { actor_email: actorEmail, ...(body.details && typeof body.details === "object" ? body.details : {}) },
      });
      if (error) throw error;
      return reply({ logged: true });
    }

    if (action === "list_error_logs") {
      const { data, error } = await admin.from("admin_error_logs")
        .select("id,source,message,details,created_at")
        .order("created_at", { ascending: false }).limit(200);
      if (error) throw error;
      return reply({ logs: data || [] });
    }

    if (action === "list") {
      const page = Math.max(1, Math.min(1000, Number(body.page) || 1));
      const perPage = Math.max(1, Math.min(100, Number(body.perPage) || 100));
      const { data, error } = await admin.auth.admin.listUsers({ page, perPage });
      if (error) throw error;
      const users = (data.users || []).map((u) => ({
        id: u.id, email: u.email || "", created_at: u.created_at || "",
        last_sign_in_at: u.last_sign_in_at || "",
        email_confirmed_at: u.email_confirmed_at || "",
        banned_until: u.banned_until || "",
        user_metadata: {
          full_name: u.user_metadata?.full_name || "",
          nickname: u.user_metadata?.nickname || "",
          phone: u.user_metadata?.phone || "",
          address: u.user_metadata?.address || "",
        },
      }));
      await audit("회원 목록 조회", null, { count: users.length });
      return reply({ users, page, perPage, total: data.total ?? null });
    }

    if (action === "update_profile") {
      const userId = String(body.user_id || "");
      if (!userId) return reply({ error: "회원 ID가 필요합니다." }, 400);
      const { data: existing, error: getError } = await admin.auth.admin.getUserById(userId);
      if (getError || !existing.user) return reply({ error: "회원을 찾을 수 없습니다." }, 404);
      const allowed = ["full_name", "nickname", "phone", "address"];
      const patch: Record<string, string> = {};
      for (const key of allowed) patch[key] = String(body.profile?.[key] ?? "").trim();
      if (!patch.full_name || !patch.nickname) return reply({ error: "이름과 닉네임은 필수입니다." }, 400);
      const { data, error } = await admin.auth.admin.updateUserById(userId, {
        user_metadata: { ...(existing.user.user_metadata || {}), ...patch },
      });
      if (error) throw error;
      await audit("회원 정보 수정", userId, { fields: Object.keys(patch) });
      return reply({ updated: true, user_id: data.user.id });
    }

    if (action === "ban_user") {
      const userId = String(body.user_id || "");
      const duration = String(body.duration || "");
      const allowedDurations = ["24h", "168h", "720h", "876000h"];
      if (!userId) return reply({ error: "회원 ID가 필요합니다." }, 400);
      if (userId === user.id) return reply({ error: "현재 로그인한 관리자 계정은 차단할 수 없습니다." }, 400);
      if (!allowedDurations.includes(duration)) return reply({ error: "허용되지 않은 차단 기간입니다." }, 400);
      const { data, error } = await admin.auth.admin.updateUserById(userId, { ban_duration: duration });
      if (error) throw error;
      await audit("회원 차단", userId, { duration });
      return reply({ banned: true, user_id: data.user.id, banned_until: data.user.banned_until || "" });
    }

    if (action === "unban_user") {
      const userId = String(body.user_id || "");
      if (!userId) return reply({ error: "회원 ID가 필요합니다." }, 400);
      if (userId === user.id) return reply({ error: "현재 로그인한 관리자 계정은 차단 해제 대상이 아닙니다." }, 400);
      const { data, error } = await admin.auth.admin.updateUserById(userId, { ban_duration: "none" });
      if (error) throw error;
      await audit("회원 차단 해제", userId);
      return reply({ unbanned: true, user_id: data.user.id });
    }

    if (action === "list_data") {
      const { data, error } = await admin.from("user_data")
        .select("user_id,payload,updated_at")
        .order("updated_at", { ascending: false })
        .limit(500);
      if (error) throw error;
      await audit("회원 데이터 조회", null, { count: (data || []).length });
      return reply({ records: data || [] });
    }

    if (action === "restore_data") {
      const records = body.records;
      if (!Array.isArray(records) || records.length < 1 || records.length > 500) {
        return reply({ error: "복구 데이터는 1~500건이어야 합니다." }, 400);
      }
      if (JSON.stringify(records).length > 5_000_000) {
        return reply({ error: "백업 파일 크기가 너무 큽니다. 5MB 이하로 나눠 복구해 주세요." }, 413);
      }
      const rows: { user_id: string; payload: Record<string, unknown>; updated_at?: string }[] = [];
      for (const item of records) {
        if (!item || typeof item.user_id !== "string" || !item.user_id ||
            typeof item.payload !== "object" || item.payload === null || Array.isArray(item.payload)) {
          return reply({ error: "백업 데이터의 회원 ID 또는 payload 형식이 올바르지 않습니다." }, 400);
        }
        rows.push({ user_id: item.user_id, payload: item.payload });
      }
      const { error } = await admin.from("user_data").upsert(rows, { onConflict: "user_id" });
      if (error) throw error;
      await audit("회원 데이터 복구", null, { count: rows.length });
      return reply({ restored: rows.length });
    }

    if (action === "delete_user") {
      const userId = String(body.user_id || "");
      if (!userId) return reply({ error: "회원 ID가 필요합니다." }, 400);
      if (userId === user.id) return reply({ error: "현재 로그인한 관리자 계정은 이 화면에서 삭제할 수 없습니다." }, 400);
      if (body.confirmation !== "DELETE_MEMBER") return reply({ error: "삭제 확인값이 올바르지 않습니다." }, 400);
      const { error } = await admin.auth.admin.deleteUser(userId);
      if (error) throw error;
      await audit("회원 계정 삭제", null, { deleted_user_id: userId });
      return reply({ deleted: true, user_id: userId });
    }

    return reply({ error: "지원하지 않는 요청입니다." }, 400);
  } catch (error) {
    console.error("MOAMOA admin API error:", error);
    if (adminClient) {
      const message = error instanceof Error ? error.message : String(error);
      const { error: logError } = await adminClient.from("admin_error_logs").insert({
        source: "admin-users:" + currentAction,
        message: message.slice(0, 1500),
        details: { action: currentAction, actor_email: actorEmail },
      });
      if (logError) console.error("MOAMOA error log write failed:", logError.message);
    }
    return reply({ error: "관리자 요청을 처리하지 못했습니다. 서버 로그를 확인해 주세요." }, 500);
  }
});
