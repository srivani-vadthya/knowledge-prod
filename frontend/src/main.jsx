import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Bot,
  CheckCircle2,
  ChevronsLeft,
  ChevronsRight,
  Database,
  FileText,
  Loader2,
  LogOut,
  RefreshCw,
  Search,
  Send,
  Shield,
  Sparkles,
  UploadCloud,
  UserRound,
  Wrench,
} from "lucide-react";
import "./styles.css";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const ADMIN_CODE = import.meta.env.VITE_ADMIN_CODE || "admin123";
const USER_CODE = import.meta.env.VITE_USER_CODE || "";

function classNames(...values) {
  return values.filter(Boolean).join(" ");
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" ? payload.detail || payload.error : payload;
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return payload;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(Math.round(value || 0));
}

function StatusPill({ health, loading }) {
  const healthy = health?.status === "healthy";
  const degraded = health?.status === "degraded";

  return (
    <span className={classNames("status-pill", healthy && "healthy", degraded && "degraded")}>
      {loading ? <Loader2 className="spin" size={15} /> : healthy ? <CheckCircle2 size={15} /> : <Activity size={15} />}
      {loading ? "Checking" : health?.status || "Unknown"}
    </span>
  );
}

function renderInlineMarkdown(text) {
  const parts = String(text).split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

function MarkdownAnswer({ text }) {
  const lines = String(text || "").split(/\r?\n/);
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const HeadingTag = heading[1].length <= 2 ? "h3" : "h4";
      blocks.push(<HeadingTag key={index}>{renderInlineMarkdown(heading[2])}</HeadingTag>);
      index += 1;
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const items = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^[-*]\s+/, ""));
        index += 1;
      }
      blocks.push(
        <ul key={index}>
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const items = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^\d+\.\s+/, ""));
        index += 1;
      }
      blocks.push(
        <ol key={index}>
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInlineMarkdown(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    const paragraph = [trimmed];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(#{1,4})\s+/.test(lines[index].trim()) &&
      !/^[-*]\s+/.test(lines[index].trim()) &&
      !/^\d+\.\s+/.test(lines[index].trim())
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push(<p key={index}>{renderInlineMarkdown(paragraph.join(" "))}</p>);
  }

  return <div className="markdown-answer">{blocks}</div>;
}

function LoginScreen({ onLogin }) {
  const [role, setRole] = useState("user");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  function submit(event) {
    event.preventDefault();
    const displayName = name.trim();
    const expectedCode = role === "admin" ? ADMIN_CODE : USER_CODE;

    if (!displayName) {
      setError("Please enter your name before continuing.");
      return;
    }

    if (expectedCode && code !== expectedCode) {
      setError("Access code is not correct for this role.");
      return;
    }

    onLogin({ role, name: displayName });
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="login-brand">
          <div className="brand-mark">
            <Sparkles size={20} />
          </div>
          <div>
            <h1>Knowledge Assistant</h1>
            <p>Sign in to continue</p>
          </div>
        </div>

        <form className="login-form" onSubmit={submit}>
          <label>
            Display name
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Srivani" />
          </label>

          <div className="role-toggle" aria-label="Select role">
            <button className={classNames(role === "user" && "active")} type="button" onClick={() => setRole("user")}>
              <UserRound size={16} />
              User
            </button>
            <button className={classNames(role === "admin" && "active")} type="button" onClick={() => setRole("admin")}>
              <Shield size={16} />
              Admin
            </button>
          </div>

          <label>
            Access code
            <input
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder={role === "admin" ? "Admin code" : "Optional user code"}
              type="password"
            />
          </label>

          {error && <div className="login-error">{error}</div>}

          <button className="primary-button" type="submit">
            Continue
          </button>
        </form>
      </section>
    </main>
  );
}

function MetricCard({ label, value, icon }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function UploadSection({ uploadState, onUpload }) {
  const fileInputRef = useRef(null);

  return (
    <section className="side-section">
      <div className="section-title">
        <span>Upload docs</span>
        <UploadCloud size={16} />
      </div>
      <input
        ref={fileInputRef}
        className="file-input"
        type="file"
        accept=".pdf,.txt,.docx,.csv,.xlsx,.xls,.pptx,.ppt,.md"
        onChange={(event) => onUpload(event.target.files?.[0], () => {
          if (fileInputRef.current) fileInputRef.current.value = "";
        })}
      />
      <button className="upload-drop" type="button" onClick={() => fileInputRef.current?.click()}>
        {uploadState.loading ? <Loader2 className="spin" size={18} /> : <UploadCloud size={18} />}
        <span>{uploadState.loading ? "Indexing..." : "Choose document"}</span>
        <small>PDF, DOCX, XLSX, PPTX, MD, CSV, TXT</small>
      </button>
      {uploadState.message && (
        <p className={classNames("upload-message", uploadState.error && "error")}>{uploadState.message}</p>
      )}
    </section>
  );
}

function DocumentsSection({ documents, documentsLoading }) {
  return (
    <section className="side-section">
      <div className="section-title">
        <span>Uploaded docs</span>
        <Database size={16} />
      </div>
      <div className="doc-list">
        {documentsLoading && (
          <div className="doc-item muted-item">
            <Loader2 className="spin" size={14} />
            Loading documents
          </div>
        )}
        {!documentsLoading && documents.length === 0 && (
          <div className="doc-empty">No documents indexed yet.</div>
        )}
        {documents.map((document) => (
          <div className="doc-item" key={document}>
            <FileText size={14} />
            <span title={document}>{document}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function AdminPanel({ metrics, health, healthLoading, syncState, onRefresh, onClearChat, onSyncServiceNow }) {
  return (
    <section className="admin-panel">
      <div className="section-title">
        <span>Admin metrics</span>
        <BarChart3 size={16} />
      </div>
      <div className="metric-grid">
        <MetricCard label="Requests" value={formatNumber(metrics?.requests_total)} icon={<Activity size={15} />} />
        <MetricCard label="Errors" value={formatNumber(metrics?.errors_total)} icon={<AlertCircle size={15} />} />
        <MetricCard label="Avg ms" value={formatNumber(metrics?.avg_response_time_ms)} icon={<Activity size={15} />} />
        <MetricCard label="Tokens" value={formatNumber(metrics?.tokens_total)} icon={<Sparkles size={15} />} />
        <MetricCard label="Cost" value={`$${metrics?.estimated_cost_usd?.toFixed(2) || "0.00"}`} icon={<Sparkles size={15} />} />
      </div>

      <div className="maintenance-box">
        <div className="section-title">
          <span>Maintenance</span>
          <Wrench size={16} />
        </div>
        <div className="maintenance-row">
          <span>API</span>
          <StatusPill health={health} loading={healthLoading} />
        </div>
        <div className="maintenance-row">
          <span>P95</span>
          <strong>{formatNumber(metrics?.p95_response_time_ms)} ms</strong>
        </div>
        <div className="maintenance-row">
          <span>P99</span>
          <strong>{formatNumber(metrics?.p99_response_time_ms)} ms</strong>
        </div>
        <button className="mini-button" type="button" onClick={onRefresh}>
          <RefreshCw size={15} />
          Refresh system
        </button>
        <button className="mini-button" type="button" onClick={onSyncServiceNow} disabled={syncState.loading}>
          {syncState.loading ? <Loader2 className="spin" size={15} /> : <Database size={15} />}
          {syncState.loading ? "Syncing ServiceNow" : "Sync ServiceNow"}
        </button>
        <button className="mini-button subtle" type="button" onClick={onClearChat}>
          Clear chat
        </button>
        {syncState.message && (
          <p className={classNames("upload-message", syncState.error && "error")}>{syncState.message}</p>
        )}
      </div>
    </section>
  );
}

function Sidebar({
  session,
  metrics,
  documents,
  documentsLoading,
  uploadState,
  health,
  healthLoading,
  syncState,
  collapsed,
  onUpload,
  onRefresh,
  onSyncServiceNow,
  onNewChat,
  onClearChat,
  onLogout,
  onToggleCollapse,
}) {
  const isAdmin = session.role === "admin";

  return (
    <aside className={classNames("sidebar", collapsed && "collapsed")}>
      <div className="brand-block">
        <div className="brand-mark">
          <Sparkles size={19} />
        </div>
        <div className="hide-when-collapsed">
          <strong>Knowledge AI</strong>
          <span>{isAdmin ? "Admin console" : "User workspace"}</span>
        </div>
      </div>

      <button
        className="collapse-button"
        type="button"
        onClick={onToggleCollapse}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronsRight size={17} /> : <ChevronsLeft size={17} />}
      </button>

      <button className="new-chat-button" type="button" onClick={onNewChat}>
        <Bot size={17} />
        <span className="hide-when-collapsed">New conversation</span>
      </button>

      {!collapsed && (
        <>
          <div className="sidebar-section">
            <span className="section-label">Session</span>
            <div className="profile-card">
              <div className="profile-avatar">{session.name.slice(0, 1).toUpperCase()}</div>
              <div>
                <strong>{session.name}</strong>
                <span>{isAdmin ? "Administrator" : "User"}</span>
              </div>
            </div>
          </div>

          {isAdmin && (
            <>
              <UploadSection uploadState={uploadState} onUpload={onUpload} />
              <DocumentsSection documents={documents} documentsLoading={documentsLoading} />
              <AdminPanel
                metrics={metrics}
                health={health}
                healthLoading={healthLoading}
                syncState={syncState}
                onRefresh={onRefresh}
                onSyncServiceNow={onSyncServiceNow}
                onClearChat={onClearChat}
              />
            </>
          )}

          {!isAdmin && (
            <section className="side-section user-note">
              <div className="section-title">
                <span>Access</span>
                <Shield size={16} />
              </div>
              <p>You can chat with indexed documents. Admin tools are hidden for this session.</p>
            </section>
          )}
        </>
      )}

      <div className="sidebar-spacer" />

      <button className="logout-button" type="button" onClick={onLogout}>
        <LogOut size={16} />
        <span className="hide-when-collapsed">Sign out</span>
      </button>
    </aside>
  );
}

function Header({ session, health, healthLoading, onRefresh }) {
  return (
    <header className="topbar">
      <div>
        <span className="eyebrow">{session.role === "admin" ? "Admin mode" : "User mode"}</span>
        <h1>Knowledge Assistant</h1>
      </div>
      <div className="topbar-actions">
        <button className="ghost-button" type="button" onClick={onRefresh}>
          <RefreshCw size={16} />
          Refresh
        </button>
        <StatusPill health={health} loading={healthLoading} />
      </div>
    </header>
  );
}

function calculateCost(tokensInput, tokensOutput, model = "gpt-4o-mini") {
  const pricing = {
    "gpt-4o-mini": { input: 0.150, output: 0.600 },
    "gpt-3.5-turbo": { input: 0.500, output: 1.500 },
    "gpt-4": { input: 30.000, output: 60.000 },
    "gpt-4-turbo": { input: 10.000, output: 30.000 },
  };
  const rates = pricing[model] || pricing["gpt-4o-mini"];
  const inputCost = (tokensInput / 1_000_000) * rates.input;
  const outputCost = (tokensOutput / 1_000_000) * rates.output;
  return (inputCost + outputCost).toFixed(5);
}

function Message({ message }) {
  const isUser = message.role === "user";
  const showEvidence = !isUser && message.showEvidence;
  const hasTokens = !isUser && message.tokens;

  return (
    <article className={classNames("message", isUser && "user-message")}>
      <div className="avatar">{isUser ? "You" : <Bot size={17} />}</div>
      <div className="message-body">
        {isUser ? <p>{message.content}</p> : <MarkdownAnswer text={message.content} />}

        {showEvidence && message.confidence && (
          <div className="answer-meta">
            <span className="confidence">{message.confidence.category}</span>
            <span>{Math.round(message.confidence.score * 100)}% confidence</span>
            <span>Retrieved from indexed documents</span>
          </div>
        )}

        {hasTokens && (
          <div className="answer-meta token-meta">
            <span>🔢 {formatNumber(message.tokens.input)} in</span>
            <span>🔤 {formatNumber(message.tokens.output)} out</span>
            <span>💰 ${calculateCost(message.tokens.input, message.tokens.output)}</span>
          </div>
        )}

        {showEvidence && message.sources?.length > 0 && (
          <div className="sources evidence-panel">
            <div className="evidence-title">Retrieved from</div>
            {message.sources.map((source, index) => (
              <div className="source" key={`${source.document}-${source.page}-${index}`}>
                <FileText size={15} />
                <span>{source.document}</span>
                {source.page && <small>Page {source.page}</small>}
                <small>{Math.round(source.relevance_score * 100)}%</small>
              </div>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

function EmptyState({ onUsePrompt }) {
  const prompts = [
    "What documents are indexed?",
    "Summarize the uploaded knowledge base.",
    "Compare the key details across documents.",
  ];

  return (
    <div className="empty-state">
      <div className="empty-orb">
        <Search size={28} />
      </div>
      <h2>Ask your knowledge base</h2>
      <p>Search, summarize, compare, and verify answers from your indexed documents.</p>
      <div className="prompt-row">
        {prompts.map((prompt) => (
          <button key={prompt} type="button" onClick={() => onUsePrompt(prompt)}>
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function App() {
  const [session, setSession] = useState(() => {
    const saved = localStorage.getItem("knowledge-assistant-session");
    return saved ? JSON.parse(saved) : null;
  });
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [healthLoading, setHealthLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [uploadState, setUploadState] = useState({ loading: false, message: "", error: false });
  const [syncState, setSyncState] = useState({ loading: false, message: "", error: false });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const transcriptRef = useRef(null);

  const canAsk = useMemo(() => input.trim().length >= 2 && !asking, [asking, input]);

  function handleLogin(nextSession) {
    localStorage.setItem("knowledge-assistant-session", JSON.stringify(nextSession));
    setSession(nextSession);
  }

  function logout() {
    localStorage.removeItem("knowledge-assistant-session");
    setSession(null);
    setMessages([]);
    setError("");
  }

  async function refreshDocuments() {
    setDocumentsLoading(true);
    try {
      const result = await requestJson("/documents");
      setDocuments(result.documents || []);
    } catch {
      setDocuments([]);
    } finally {
      setDocumentsLoading(false);
    }
  }

  async function refreshStatus() {
    setHealthLoading(true);
    try {
      const [nextHealth, nextMetrics] = await Promise.all([
        requestJson("/health"),
        requestJson("/metrics").catch(() => null),
      ]);
      setHealth(nextHealth);
      setMetrics(nextMetrics);
    } catch (err) {
      setHealth({ status: "offline", message: err.message });
    } finally {
      setHealthLoading(false);
    }
  }

  async function refreshAdminData() {
    await Promise.all([refreshStatus(), refreshDocuments()]);
  }

  async function askQuestion(questionText = input) {
    const question = questionText.trim();
    if (question.length < 2 || asking) return;

    setError("");
    setAsking(true);
    setInput("");
    setMessages((current) => [...current, { role: "user", content: question }]);

    try {
      const result = await requestJson("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, platform: "web", user_id: session?.name }),
      });
      const sources = result.sources || [];
      const showEvidence = result.intent === "documentation_question" && sources.length > 0;

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: result.answer,
          confidence: showEvidence
            ? {
                score: result.confidence_score,
                category: result.confidence_category,
                fromDocuments: result.is_from_documents,
              }
            : null,
          sources,
          showEvidence,
          tokens: result.tokens_total
            ? {
                input: result.tokens_input || 0,
                output: result.tokens_output || 0,
                total: result.tokens_total || 0,
              }
            : null,
        },
      ]);
      refreshStatus();
    } catch (err) {
      setError(err.message);
      setMessages((current) => [
        ...current,
        { role: "assistant", content: "I could not process that question. Check the API configuration and try again." },
      ]);
    } finally {
      setAsking(false);
    }
  }

  async function uploadDocument(file, resetInput) {
    if (!file || uploadState.loading) return;

    const formData = new FormData();
    formData.append("file", file);
    setUploadState({ loading: true, message: `Uploading ${file.name}...`, error: false });

    try {
      const result = await requestJson("/upload", {
        method: "POST",
        body: formData,
      });
      setUploadState({
        loading: false,
        message: `${result.filename} indexed with ${result.chunks_indexed} chunks.`,
        error: false,
      });
      refreshAdminData();
    } catch (err) {
      setUploadState({ loading: false, message: err.message, error: true });
    } finally {
      resetInput?.();
    }
  }

  async function syncServiceNow() {
    if (syncState.loading) return;

    setSyncState({ loading: true, message: "Fetching ServiceNow articles...", error: false });
    try {
      const result = await requestJson("/sync/servicenow", { method: "POST" });
      setSyncState({
        loading: false,
        message: `Indexed ${result.indexed} chunks from ${result.articles} articles.`,
        error: false,
      });
      refreshAdminData();
    } catch (err) {
      setSyncState({ loading: false, message: err.message, error: true });
    }
  }

  useEffect(() => {
    if (session) {
      refreshStatus();
      if (session.role === "admin") {
        refreshDocuments();
      }
    }
  }, [session]);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, asking]);

  if (!session) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <main className={classNames("app-shell", sidebarCollapsed && "sidebar-collapsed")}>
      <Sidebar
        session={session}
        metrics={metrics}
        documents={documents}
        documentsLoading={documentsLoading}
        uploadState={uploadState}
        health={health}
        healthLoading={healthLoading}
        syncState={syncState}
        collapsed={sidebarCollapsed}
        onUpload={uploadDocument}
        onRefresh={refreshAdminData}
        onSyncServiceNow={syncServiceNow}
        onNewChat={() => {
          setMessages([]);
          setError("");
        }}
        onClearChat={() => setMessages([])}
        onLogout={logout}
        onToggleCollapse={() => setSidebarCollapsed((value) => !value)}
      />

      <section className="workspace">
        <Header session={session} health={health} healthLoading={healthLoading} onRefresh={refreshAdminData} />

        {error && (
          <div className="error-banner">
            <AlertCircle size={18} />
            {error}
          </div>
        )}

        <div className="transcript" ref={transcriptRef}>
          {messages.length === 0 ? (
            <EmptyState onUsePrompt={(prompt) => askQuestion(prompt)} />
          ) : (
            messages.map((message, index) => <Message key={`${message.role}-${index}`} message={message} />)
          )}
          {asking && (
            <article className="message">
              <div className="avatar">
                <Bot size={18} />
              </div>
              <div className="message-body loading-line">
                <Loader2 className="spin" size={18} />
                Searching and drafting an answer...
              </div>
            </article>
          )}
        </div>

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            askQuestion();
          }}
        >
          <div>
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask a question about your documents..."
              maxLength={1000}
            />
            <button type="submit" disabled={!canAsk} aria-label="Send question">
              {asking ? <Loader2 className="spin" size={19} /> : <Send size={19} />}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
