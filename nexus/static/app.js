const basePath = window.location.pathname.startsWith("/nexus") ? "/nexus" : "";
const apiBase = `${basePath}/api`;
const RAG_MAX_FILES_PER_BATCH = 50;
const RAG_MAX_FILE_BYTES = 10 * 1024 * 1024;
const RAG_MAX_BATCH_BYTES = 50 * 1024 * 1024;
const RAG_UPLOAD_CONCURRENCY = 4;

const TRANSLATIONS = {
  pageTitle: { en: "NexusChat / AI workspace", sk: "NexusChat / AI pracovný priestor" },
  metaDescription: { en: "NexusChat — private AI workspace.", sk: "NexusChat — súkromný AI pracovný priestor." },
  skipContent: { en: "Skip to main content", sk: "Preskočiť na hlavný obsah" },
  heroLead: { en: "Thoughts in.", sk: "Myšlienky dnu." },
  heroAccent: { en: "Clarity out.", sk: "Jasnosť von." },
  heroCopy: { en: "Your private AI workspace for analysis, creation, and decisions. Conversations stay under your account.", sk: "Tvoj súkromný AI pracovný priestor pre analýzu, tvorbu a rozhodnutia. Konverzácie zostávajú pod tvojím účtom." },
  language: { en: "Language", sk: "Jazyk" },
  welcomeBack: { en: "Welcome back", sk: "Vitaj späť" },
  createNexus: { en: "Create your Nexus", sk: "Vytvor si Nexus" },
  signInSubtitle: { en: "Sign in to your Nexus workspace.", sk: "Prihlás sa do svojho Nexus priestoru." },
  registerSubtitle: { en: "One account. All your conversations.", sk: "Jeden účet. Všetky tvoje konverzácie." },
  authTabs: { en: "Sign in or register", sk: "Prihlásenie alebo registrácia" },
  signIn: { en: "Sign in", sk: "Prihlásenie" },
  newAccount: { en: "New account", sk: "Nový účet" },
  nameOrEmail: { en: "Name or e-mail", sk: "Meno alebo e-mail" },
  nameOrEmailPlaceholder: { en: "Your name or e-mail", sk: "Tvoje meno alebo e-mail" },
  password: { en: "Password", sk: "Heslo" },
  openNexus: { en: "Open Nexus", sk: "Otvoriť Nexus" },
  name: { en: "Name", sk: "Meno" },
  yourName: { en: "Your name", sk: "Tvoje meno" },
  email: { en: "E-mail", sk: "E-mail" },
  emailPlaceholder: { en: "you@example.com", sk: "ty@example.com" },
  passwordPlaceholder: { en: "Min. 10 characters", sk: "Min. 10 znakov" },
  passwordRules: { en: "Upper-case, lower-case, a number, and at least 10 characters.", sk: "Veľké a malé písmeno, číslo, aspoň 10 znakov." },
  createAccount: { en: "Create account", sk: "Vytvoriť účet" },
  authFootnote: { en: "By continuing, you agree to securely store your chat history on this server.", sk: "Pokračovaním súhlasíš s bezpečným uložením histórie chatu na tomto serveri." },
  closeMenu: { en: "Close menu", sk: "Zavrieť menu" },
  openMenu: { en: "Open menu", sk: "Otvoriť menu" },
  mainNavigation: { en: "Main navigation", sk: "Hlavná navigácia" },
  conversations: { en: "Conversations", sk: "Konverzácie" },
  administration: { en: "Administration", sk: "Administrácia" },
  activeModel: { en: "ACTIVE MODEL", sk: "AKTÍVNY MODEL" },
  user: { en: "User", sk: "Používateľ" },
  administrator: { en: "Administrator", sk: "Administrátor" },
  logout: { en: "Sign out", sk: "Odhlásiť sa" },
  deleteConversation: { en: "Delete conversation", sk: "Vymazať konverzáciu" },
  assistantChats: { en: "Separate assistant chats", sk: "Samostatné chaty asistentov" },
  generalAssistant: { en: "general assistant", sk: "všeobecný asistent" },
  infraSource: { en: "Infra Agent data source", sk: "Zdroj údajov Infra Agenta" },
  infraSourceLabel: { en: "INFRA SOURCE", sk: "ZDROJ INFRA" },
  lastMinute: { en: "last minute", sk: "posledná minúta" },
  nowAdmin: { en: "now · admin", sk: "teraz · admin" },
  message: { en: "Message", sk: "Správa" },
  sendMessage: { en: "Send message", sk: "Odoslať správu" },
  send: { en: "send ·", sk: "odoslať ·" },
  newLine: { en: "new line", sk: "nový riadok" },
  controlCenter: { en: "Control center", sk: "Riadiace centrum" },
  controlCopy: { en: "Accounts, usage, and AI behavior in one place.", sk: "Účty, používanie a správanie AI na jednom mieste." },
  registeredAccounts: { en: "registered accounts", sk: "registrovaných účtov" },
  activeAccounts: { en: "active accounts", sk: "aktívnych účtov" },
  conversationsMetric: { en: "conversations", sk: "konverzácií" },
  storedMessages: { en: "stored messages", sk: "uložených správ" },
  users: { en: "Users", sk: "Používatelia" },
  loading: { en: "Loading…", sk: "Načítavam…" },
  loginName: { en: "Login name", sk: "Prihlasovacie meno" },
  loginNamePlaceholder: { en: "E.g. Jane Smith", sk: "Napr. Ján Novák" },
  temporaryPassword: { en: "Temporary password", sk: "Dočasné heslo" },
  generatedPasswordPlaceholder: { en: "Create or generate a password", sk: "Vytvor alebo vygeneruj heslo" },
  generate: { en: "GENERATE", sk: "GENEROVAŤ" },
  copy: { en: "COPY", sk: "KOPÍROVAŤ" },
  role: { en: "Role", sk: "Rola" },
  nameLoginNote: { en: "The name is used for sign-in. No e-mail is required.", sk: "Meno sa používa na prihlásenie. E-mail nie je potrebný." },
  account: { en: "Account", sk: "Účet" },
  status: { en: "Status", sk: "Stav" },
  created: { en: "Created", sk: "Vytvorený" },
  primaryModel: { en: "Primary model", sk: "Hlavný model" },
  loadingCatalog: { en: "Loading model catalog…", sk: "Načítavam katalóg modelov…" },
  systemInstructions: { en: "System instructions", sk: "Systémové inštrukcie" },
  saveConfiguration: { en: "Save configuration", sk: "Uložiť konfiguráciu" },
  ragToggle: { en: "Enable or disable RAG", sk: "Zapnúť alebo vypnúť RAG" },
  ragCopy: { en: "Local knowledge base. Relevant passages are attached to the question and sources are shown with the answer.", sk: "Lokálna znalostná báza. Relevantné pasáže sa pripájajú k otázke a v odpovedi sa zobrazia zdroje." },
  maxPassages: { en: "Max. passages", sk: "Max. počet pasáží" },
  addFiles: { en: "＋ ADD OR DROP FILES", sk: "＋ PRIDAŤ ALEBO PRETIAHNUŤ SÚBORY" },
  fileLimits: { en: "TXT, MD, JSON, YAML, CSV, or LOG · max 50 at once · 10 MB/file", sk: "TXT, MD, JSON, YAML, CSV alebo LOG · max 50 naraz · 10 MB/súbor" },
  infraToggle: { en: "Enable or disable Infra Agent", sk: "Zapnúť alebo vypnúť Infra Agenta" },
  infraCopy: { en: "Switchable one-minute snapshot or LIVE read-only check. It has no unrestricted shell and cannot change the server.", sk: "Prepínateľný minútový snapshot alebo LIVE read-only kontrola. Nemá voľný shell a nevie meniť server." },
  snapshotUnavailable: { en: "SNAPSHOT UNAVAILABLE", sk: "SNAPSHOT NEDOSTUPNÝ" },
  adminsOnly: { en: "Administrators only", sk: "Iba administrátori" },
  allowLive: { en: "Allow LIVE for admins", sk: "Povoliť LIVE adminom" },
  infraBoundary: { en: "CPU · RAM · disk · ports · TLS · health · approved systemd services", sk: "CPU · RAM · disk · porty · TLS · health · povolené systemd služby" },
  dataToggle: { en: "Enable or disable SQL Report Agent", sk: "Zapnúť alebo vypnúť SQL Report Agenta" },
  dataCopy: { en: "It turns a question into read-only SQL, runs it against an isolated fictional database, and returns a finished management report.", sk: "Z otázky vytvorí read-only SQL, vykoná ho nad izolovanou fiktívnou databázou a vráti hotový manažérsky report." },
  syntheticBoundary: { en: "No real accounts or chats · SELECT/WITH · max 100 rows · time limit", sk: "Žiadne reálne účty ani chaty · SELECT/WITH · max 100 riadkov · časový limit" },
  fictionalSchema: { en: "Fictional schema", sk: "Fiktívna schéma" },
  tryAsking: { en: "TRY ASKING", sk: "SKÚS SA OPÝTAŤ" },
  exampleSales: { en: "“Compare revenue by country and segment.”", sk: "„Porovnaj tržby podľa krajín a segmentov.“" },
  exampleMargin: { en: "“Which products have the highest margin?”", sk: "„Ktoré produkty majú najvyššiu maržu?“" },
  exampleSla: { en: "“Create an SLA report for support tickets.”", sk: "„Sprav SLA report support ticketov.“" },
  unavailableTime: { en: "unavailable time", sk: "nedostupný čas" },
  requestFailed: { en: "The request could not be completed.", sk: "Požiadavku sa nepodarilo dokončiť." },
  checking: { en: "Checking…", sk: "Overujem…" },
  conversationDeletePrompt: { en: "Delete conversation “{title}”?", sk: "Vymazať konverzáciu „{title}“?" },
  conversationDeleted: { en: "Conversation deleted.", sk: "Konverzácia bola vymazaná." },
  accountsCount: { en: "{count} accounts", sk: "{count} účtov" },
  catalogUnavailable: { en: "Catalog unavailable · custom model ID still works", sk: "Katalóg je nedostupný · vlastný model ID funguje" },
  catalogCount: { en: "{count} models · you can enter a custom model ID", sk: "{count} modelov · môžeš zadať vlastný model ID" },
  contextUnknown: { en: "context not specified", sk: "kontext neuvedený" },
  context: { en: "context", sk: "kontext" },
  perMillionTokens: { en: "per 1M tokens", sk: "za 1M tokenov" },
  noDocuments: { en: "No documents yet.", sk: "Zatiaľ bez dokumentov." },
  passages: { en: "{count} passages · {chars}k characters", sk: "{count} pasáží · {chars}k znakov" },
  remove: { en: "REMOVE", sk: "ODSTRÁNIŤ" },
  removeDocumentLabel: { en: "Remove document {name}", sk: "Odstrániť dokument {name}" },
  uploadInProgress: { en: "A previous batch is still uploading.", sk: "Predchádzajúca dávka sa ešte nahráva." },
  tooManyFiles: { en: "You can add at most {count} files at once.", sk: "Naraz môžeš pridať najviac {count} súborov." },
  fileTooLarge: { en: "{name} is larger than 10 MB.", sk: "{name} je väčší ako 10 MB." },
  batchTooLarge: { en: "The batch is larger than 50 MB. Split it into multiple uploads.", sk: "Celá dávka je väčšia ako 50 MB. Rozdeľ ju na viac uploadov." },
  uploading: { en: "Uploading {done}/{total}…", sk: "Nahrávam {done}/{total}…" },
  uploadPartial: { en: "Done: {success} added · {failed} failed", sk: "Hotovo: {success} pridaných · {failed} zlyhalo" },
  uploadDone: { en: "Done: {count} files added", sk: "Hotovo: {count} súborov pridaných" },
  filesAdded: { en: "{count} files were added to the knowledge base.", sk: "{count} súborov bolo pridaných do znalostnej bázy." },
  removeDocumentPrompt: { en: "Remove this document from the knowledge base?", sk: "Odstrániť dokument zo znalostnej bázy?" },
  documentRemoved: { en: "Document removed.", sk: "Dokument bol odstránený." },
  loginPrefix: { en: "Login: {name}", sk: "Prihlásenie: {name}" },
  userRoleLabel: { en: "Role for {name}", sk: "Rola používateľa {name}" },
  deactivateUser: { en: "Deactivate user {name}", sk: "Deaktivovať používateľa {name}" },
  activateUser: { en: "Activate user {name}", sk: "Aktivovať používateľa {name}" },
  userUpdated: { en: "User updated.", sk: "Používateľ bol aktualizovaný." },
  accountCreated: { en: "{role} {name} was created.", sk: "{role} {name} bol vytvorený." },
  passwordGenerated: { en: "Secure password generated.", sk: "Bezpečné heslo bolo vygenerované." },
  passwordCopied: { en: "Password copied.", sk: "Heslo bolo skopírované." },
  passwordSelected: { en: "The password is selected. Copy it with Ctrl+C.", sk: "Heslo je označené. Skopíruj ho klávesmi Ctrl+C." },
  saving: { en: "Saving…", sk: "Ukladám…" },
  settingsSaved: { en: "AI configuration saved.", sk: "AI konfigurácia bola uložená." },
  loggedOut: { en: "You have signed out.", sk: "Bol si odhlásený." },
  shortened: { en: " · shortened", sk: " · skrátené" },
  rows: { en: "rows", sk: "riadkov" },
  showSql: { en: "Show executed SQL query", sk: "Zobraziť vykonaný SQL dotaz" },
  sqlUnavailable: { en: "SQL query is unavailable.", sk: "SQL dotaz nie je dostupný." },
  preparing: { en: "{agent} is preparing a response", sk: "{agent} pripravuje odpoveď" },
  thinking: { en: "THINKING", sk: "PREMÝŠĽA" },
};

function storedLanguage() {
  try {
    return window.localStorage.getItem("nexus_language") === "sk" ? "sk" : "en";
  } catch {
    return "en";
  }
}

function t(key, values = {}) {
  const template = TRANSLATIONS[key]?.[state.language]
    || TRANSLATIONS[key]?.en
    || key;
  return Object.entries(values).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    template,
  );
}

const state = {
  language: storedLanguage(),
  user: null,
  conversationsByAgent: {
    general: [],
    infra: [],
    data: [],
  },
  activeConversationByAgent: {
    general: null,
    infra: null,
    data: null,
  },
  activeConversation: null,
  activeView: "chat",
  sending: false,
  agentMode: "general",
  infraSource: "snapshot",
  capabilities: null,
  models: [],
  settingsSaving: false,
  settingsQueued: false,
  ragUploading: false,
};

const AGENT_WORKSPACES_SK = {
  general: {
    shortLabel: "NEXUS",
    historyLabel: "NEXUS HISTÓRIA",
    sectionLabel: "NEXUS CHAT",
    mark: "N",
    newChatLabel: "Nová konverzácia",
    emptyEyebrow: "NEXUS INTELLIGENCE / READY",
    emptyTitleLead: "Čo dnes",
    emptyTitleAccent: "rozpletieme?",
    emptyDescription: "Začni otázkou alebo si vyber jeden zo smerov.",
    placeholder: "Napíš správu pre Nexus…",
    disclaimer: "Nexus môže urobiť chybu. Dôležité informácie si over.",
    prompts: [
      {
        index: "01 / ANALÝZA",
        title: "Rozlož problém",
        detail: "Fakty, riziká, možnosti →",
        prompt: "Analyzuj túto situáciu krok za krokom a navrhni tri realistické riešenia.",
      },
      {
        index: "02 / PLÁN",
        title: "Navrhni postup",
        detail: "Míľniky a ďalší krok →",
        prompt: "Pomôž mi vytvoriť jasný plán projektu s míľnikmi, rizikami a ďalším krokom.",
      },
      {
        index: "03 / POCHOPENIE",
        title: "Vysvetli tému",
        detail: "Jasne a bez balastu →",
        prompt: "Vysvetli mi túto tému jednoducho, ale bez straty podstatných detailov.",
      },
    ],
  },
  infra: {
    shortLabel: "INFRA",
    historyLabel: "INFRA HISTÓRIA",
    sectionLabel: "INFRA CHAT",
    mark: "I",
    newChatLabel: "Nový infra chat",
    emptyEyebrow: "INFRA AGENT / READ-ONLY",
    emptyTitleLead: "Čo na serveri",
    emptyTitleAccent: "preveríme?",
    emptyDescription: "Samostatný chat nad aktuálnym read-only snapshotom servera.",
    placeholder: "Opýtaj sa na server, služby alebo aplikácie…",
    disclaimer: "Infra Agent iba číta snapshot. Na serveri nevykonáva žiadne zmeny.",
    prompts: [
      {
        index: "01 / HEALTH",
        title: "Stav servera",
        detail: "CPU, RAM, disk a load →",
        prompt: "Skontroluj aktuálny stav servera: CPU, RAM, disk, load a upozorni ma na riziká.",
      },
      {
        index: "02 / SERVICES",
        title: "Skontroluj služby",
        detail: "Procesy a dostupnosť →",
        prompt: "Ktoré sledované služby bežia a vidíš pri niektorej problém alebo výpadok?",
      },
      {
        index: "03 / APP",
        title: "Nexus a TLS",
        detail: "Aplikácia, proxy, certifikát →",
        prompt: "Skontroluj stav Nexus aplikácie, reverzného proxy a platnosť TLS certifikátu.",
      },
    ],
  },
  data: {
    shortLabel: "DATA",
    historyLabel: "DATA HISTÓRIA",
    sectionLabel: "DATA CHAT",
    mark: "D",
    newChatLabel: "Nový SQL report",
    emptyEyebrow: "DATA AGENT / SYNTHETIC DB",
    emptyTitleLead: "Aký report",
    emptyTitleAccent: "pripravíme?",
    emptyDescription: "Samostatný priestor pre read-only SQL a reporty z fiktívnych dát.",
    placeholder: "Požiadaj o report alebo napíš read-only SQL…",
    disclaimer: "Data Agent pracuje iba s oddelenou fiktívnou databázou v read-only režime.",
    prompts: [
      {
        index: "01 / SALES",
        title: "Tržby podľa krajín",
        detail: "Výsledky a porovnanie →",
        prompt: "Sprav report tržieb podľa krajín a zoradi ich od najvyšších.",
      },
      {
        index: "02 / MARGIN",
        title: "Marža produktov",
        detail: "Top a slabé produkty →",
        prompt: "Porovnaj maržu produktov a upozorni na tri najslabšie výsledky.",
      },
      {
        index: "03 / SLA",
        title: "SLA a incidenty",
        detail: "Trend a odchýlky →",
        prompt: "Priprav report SLA a incidentov za posledné dostupné obdobie.",
      },
    ],
  },
};

const INFRA_LIVE_UI_SK = {
  sectionLabel: "INFRA LIVE",
  emptyEyebrow: "LIVE INFRA / ADMIN READ-ONLY",
  emptyTitleLead: "Čo na serveri",
  emptyTitleAccent: "zmeriame teraz?",
  emptyDescription: "Pevne povolené kontroly sa vykonajú naživo pri každej otázke.",
  placeholder: "Opýtaj sa na aktuálny stav servera…",
  disclaimer: "LIVE vykonáva iba pevné read-only kontroly bez root shellu a zmien.",
};

const AGENT_WORKSPACES_EN = {
  general: {
    shortLabel: "NEXUS",
    historyLabel: "NEXUS HISTORY",
    sectionLabel: "NEXUS CHAT",
    mark: "N",
    newChatLabel: "New conversation",
    emptyEyebrow: "NEXUS INTELLIGENCE / READY",
    emptyTitleLead: "What shall we",
    emptyTitleAccent: "untangle today?",
    emptyDescription: "Start with a question or choose one of the directions below.",
    placeholder: "Write a message to Nexus…",
    disclaimer: "Nexus can make mistakes. Verify important information.",
    prompts: [
      {
        index: "01 / ANALYSIS",
        title: "Break down a problem",
        detail: "Facts, risks, options →",
        prompt: "Analyze this situation step by step and propose three realistic solutions.",
      },
      {
        index: "02 / PLAN",
        title: "Design a plan",
        detail: "Milestones and next step →",
        prompt: "Help me create a clear project plan with milestones, risks, and the next action.",
      },
      {
        index: "03 / UNDERSTAND",
        title: "Explain a topic",
        detail: "Clear and concise →",
        prompt: "Explain this topic simply without losing the important details.",
      },
    ],
  },
  infra: {
    shortLabel: "INFRA",
    historyLabel: "INFRA HISTORY",
    sectionLabel: "INFRA CHAT",
    mark: "I",
    newChatLabel: "New infra chat",
    emptyEyebrow: "INFRA AGENT / READ-ONLY",
    emptyTitleLead: "What should we",
    emptyTitleAccent: "check on the server?",
    emptyDescription: "A separate chat over the current read-only server snapshot.",
    placeholder: "Ask about the server, services, or applications…",
    disclaimer: "Infra Agent only reads a snapshot. It makes no changes to the server.",
    prompts: [
      {
        index: "01 / HEALTH",
        title: "Server health",
        detail: "CPU, RAM, disk, and load →",
        prompt: "Check the current server state: CPU, RAM, disk, and load, and warn me about risks.",
      },
      {
        index: "02 / SERVICES",
        title: "Check services",
        detail: "Processes and availability →",
        prompt: "Which monitored services are running, and do you see any problem or outage?",
      },
      {
        index: "03 / APP",
        title: "Nexus and TLS",
        detail: "Application, proxy, certificate →",
        prompt: "Check the Nexus application, reverse proxy, and TLS certificate validity.",
      },
    ],
  },
  data: {
    shortLabel: "DATA",
    historyLabel: "DATA HISTORY",
    sectionLabel: "DATA CHAT",
    mark: "D",
    newChatLabel: "New SQL report",
    emptyEyebrow: "DATA AGENT / SYNTHETIC DB",
    emptyTitleLead: "Which report",
    emptyTitleAccent: "shall we prepare?",
    emptyDescription: "A separate workspace for read-only SQL and reports over fictional data.",
    placeholder: "Request a report or enter read-only SQL…",
    disclaimer: "Data Agent only works with an isolated fictional database in read-only mode.",
    prompts: [
      {
        index: "01 / SALES",
        title: "Revenue by country",
        detail: "Results and comparison →",
        prompt: "Create a revenue report by country and sort it from highest to lowest.",
      },
      {
        index: "02 / MARGIN",
        title: "Product margins",
        detail: "Top and weak products →",
        prompt: "Compare product margins and highlight the three weakest results.",
      },
      {
        index: "03 / SLA",
        title: "SLA and incidents",
        detail: "Trend and deviations →",
        prompt: "Prepare an SLA and incident report for the latest available period.",
      },
    ],
  },
};

const INFRA_LIVE_UI_EN = {
  sectionLabel: "INFRA LIVE",
  emptyEyebrow: "LIVE INFRA / ADMIN READ-ONLY",
  emptyTitleLead: "What should we",
  emptyTitleAccent: "measure now?",
  emptyDescription: "Fixed approved checks run live for every question.",
  placeholder: "Ask about the server's current state…",
  disclaimer: "LIVE only runs fixed read-only checks without a root shell or changes.",
};

function agentWorkspaces() {
  return state.language === "sk" ? AGENT_WORKSPACES_SK : AGENT_WORKSPACES_EN;
}

function liveInfraUi() {
  return state.language === "sk" ? INFRA_LIVE_UI_SK : INFRA_LIVE_UI_EN;
}

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const mobileSidebarQuery = window.matchMedia("(max-width: 780px)");
let staticTranslationsInitialized = false;

function applyStaticTranslations() {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);

  for (const node of nodes) {
    const normalized = node.nodeValue.replace(/\s+/g, " ").trim();
    if (!node.__nexusTranslationKey && !staticTranslationsInitialized) {
      node.__nexusTranslationKey = Object.entries(TRANSLATIONS).find(
        ([, values]) => Object.values(values).includes(normalized),
      )?.[0];
    }
    if (!node.__nexusTranslationKey) continue;
    const leading = node.nodeValue.match(/^\s*/)?.[0] || "";
    const trailing = node.nodeValue.match(/\s*$/)?.[0] || "";
    node.nodeValue = `${leading}${t(node.__nexusTranslationKey)}${trailing}`;
  }

  for (const element of $$('[placeholder], [aria-label], [title], meta[name="description"]')) {
    element.__nexusTranslationAttributes ||= {};
    for (const attribute of ["placeholder", "aria-label", "title", "content"]) {
      if (!element.hasAttribute(attribute)) continue;
      const current = element.getAttribute(attribute).replace(/\s+/g, " ").trim();
      if (!element.__nexusTranslationAttributes[attribute] && !staticTranslationsInitialized) {
        element.__nexusTranslationAttributes[attribute] = Object.entries(TRANSLATIONS).find(
          ([, values]) => Object.values(values).includes(current),
        )?.[0];
      }
      const key = element.__nexusTranslationAttributes[attribute];
      if (key) element.setAttribute(attribute, t(key));
    }
  }
  staticTranslationsInitialized = true;
}

function setLanguage(language, persist = true) {
  state.language = language === "sk" ? "sk" : "en";
  document.documentElement.lang = state.language;
  document.title = t("pageTitle");
  if (persist) {
    try {
      window.localStorage.setItem("nexus_language", state.language);
    } catch {}
  }
  applyStaticTranslations();
  $$('[data-language]').forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.language === state.language));
  });
  const authMode = $("#register-form").classList.contains("hidden") ? "login" : "register";
  setAuthMode(authMode);
  if (!state.user) return;
  $("#sidebar-user-role").textContent = state.user.role === "admin"
    ? t("administrator")
    : t("user");
  updateAgentWorkspaceUI(state.agentMode);
  renderConversationList();
  renderConversation();
  if (state.activeView === "admin") loadAdmin();
}

function show(element, visible = true) {
  if (!element) return;
  element.classList.toggle("hidden", !visible);
  element.hidden = !visible;
}

function asDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDate(value) {
  const parsed = asDate(value);
  if (!parsed) return "—";
  return new Intl.DateTimeFormat(state.language === "sk" ? "sk-SK" : "en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parsed);
}

function formatTime(value) {
  const parsed = asDate(value);
  if (!parsed) return "";
  return new Intl.DateTimeFormat(state.language === "sk" ? "sk-SK" : "en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function formatDateTime(value) {
  const parsed = asDate(value);
  if (!parsed) return t("unavailableTime");
  return new Intl.DateTimeFormat(state.language === "sk" ? "sk-SK" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(parsed);
}

function messageCountLabel(count) {
  if (state.language === "en") return count === 1 ? "1 message" : `${count} messages`;
  if (count === 1) return "1 správa";
  if (count >= 2 && count <= 4) return `${count} správy`;
  return `${count} správ`;
}

function formatUsd(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

async function api(path, options = {}) {
  const config = {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "Accept-Language": state.language,
      ...(options.headers || {}),
    },
    ...options,
  };
  const response = await fetch(`${apiBase}${path}`, config);
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail || t("requestFailed"));
    error.status = response.status;
    throw error;
  }
  return body;
}

function toast(message, type = "success") {
  const node = document.createElement("div");
  node.className = `toast ${type === "error" ? "error" : ""}`;
  node.setAttribute("role", type === "error" ? "alert" : "status");
  node.textContent = message;
  $("#toast-region").appendChild(node);
  window.setTimeout(() => node.remove(), 4200);
}

function setAuthMode(mode) {
  const login = mode === "login";
  show($("#login-form"), login);
  show($("#register-form"), !login);
  $$(".auth-tab").forEach((tab) => {
    const selected = tab.dataset.authMode === mode;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  });
  $("#auth-title").textContent = login ? t("welcomeBack") : t("createNexus");
  $("#auth-subtitle").textContent = login
    ? t("signInSubtitle")
    : t("registerSubtitle");
  show($("#auth-error"), false);
}

function setAuthLoading(form, loading) {
  const button = form.querySelector("button[type=submit]");
  button.disabled = loading;
  button.dataset.original ||= button.innerHTML;
  button.innerHTML = loading ? `<span>${t("checking")}</span><span>◌</span>` : button.dataset.original;
}

async function submitAuth(form, mode) {
  const data = Object.fromEntries(new FormData(form));
  setAuthLoading(form, true);
  show($("#auth-error"), false);
  try {
    const result = await api(`/auth/${mode}`, {
      method: "POST",
      body: JSON.stringify(data),
    });
    state.user = result.user;
    enterWorkspace();
  } catch (error) {
    $("#auth-error").textContent = error.message;
    show($("#auth-error"));
    $("#auth-error").focus();
  } finally {
    setAuthLoading(form, false);
  }
}

async function initialize() {
  setLanguage(state.language, false);
  bindEvents();
  try {
    const result = await api("/auth/me");
    state.user = result.user;
    enterWorkspace();
  } catch {
    show($("#auth-view"));
    show($("#workspace"), false);
  }
}

async function enterWorkspace() {
  show($("#auth-view"), false);
  show($("#workspace"));
  $("#sidebar-user-name").textContent = state.user.name;
  $("#sidebar-user-role").textContent =
    state.user.role === "admin" ? t("administrator") : t("user");
  $("#user-avatar").textContent = state.user.name.charAt(0).toUpperCase();
  show($("#admin-nav"), state.user.role === "admin");
  switchView("chat");
  await loadCapabilities();
  await selectAgent(state.agentMode);
}

async function loadCapabilities() {
  try {
    state.capabilities = await api("/capabilities");
    $("#sidebar-model").textContent = state.capabilities.model;
    show($("#infra-agent-option"), state.capabilities.infra_agent_available);
    show($("#data-agent-option"), state.capabilities.data_agent_available);
    show($("#infra-live-option"), state.capabilities.infra_live_available);
    if (!state.capabilities.infra_live_available && state.infraSource === "live") {
      selectInfraSource("snapshot");
    }
    if (!state.capabilities.infra_agent_available && state.agentMode === "infra") {
      await selectAgent("general");
    }
    if (!state.capabilities.data_agent_available && state.agentMode === "data") {
      await selectAgent("general");
    }
  } catch (error) {
    toast(error.message, "error");
  }
}

function conversationsFor(mode = state.agentMode) {
  return state.conversationsByAgent[mode];
}

function updateAgentWorkspaceUI(mode) {
  const baseWorkspace = agentWorkspaces()[mode];
  const workspace = mode === "infra" && state.infraSource === "live"
    ? { ...baseWorkspace, ...liveInfraUi() }
    : baseWorkspace;
  $("#workspace").dataset.agentMode = mode;
  $("#conversation-heading-label").textContent = workspace.historyLabel;
  $("#new-chat-label").textContent = workspace.newChatLabel;
  $("#current-section").textContent = workspace.sectionLabel;
  $("#empty-agent-mark").textContent = workspace.mark;
  $("#empty-eyebrow").textContent = workspace.emptyEyebrow;
  $("#empty-title-lead").textContent = workspace.emptyTitleLead;
  $("#empty-title-accent").textContent = workspace.emptyTitleAccent;
  $("#empty-description").textContent = workspace.emptyDescription;
  $("#message-input").placeholder = workspace.placeholder;
  $("#chat-agent-label").textContent = mode === "infra"
    ? `INFRA CHAT / ${state.infraSource.toUpperCase()}`
    : `${workspace.sectionLabel} / LIVE`;
  $("#agent-disclaimer").textContent = workspace.disclaimer;
  $$(".prompt-card").forEach((card, index) => {
    const prompt = workspace.prompts[index];
    card.dataset.prompt = prompt.prompt;
    card.querySelector("span").textContent = prompt.index;
    card.querySelector("strong").textContent = prompt.title;
    card.querySelector("small").textContent = prompt.detail;
  });
}

async function selectAgent(mode) {
  if (mode === "infra" && !state.capabilities?.infra_agent_available) return;
  if (mode === "data" && !state.capabilities?.data_agent_available) return;
  state.activeConversationByAgent[state.agentMode] = state.activeConversation;
  state.agentMode = mode;
  if (
    mode === "infra"
    && state.infraSource === "live"
    && !state.capabilities?.infra_live_available
  ) {
    state.infraSource = "snapshot";
  }
  state.activeConversation = state.activeConversationByAgent[mode];
  $$(".agent-option").forEach((option) => {
    const selected = option.dataset.agent === mode;
    option.classList.toggle("active", selected);
    option.setAttribute("aria-pressed", String(selected));
  });
  show(
    $("#infra-source-switcher"),
    mode === "infra" && state.capabilities?.infra_live_available,
  );
  $$(".infra-source-option").forEach((option) => {
    const selected = option.dataset.infraSource === state.infraSource;
    option.classList.toggle("active", selected);
    option.setAttribute("aria-pressed", String(selected));
  });
  updateAgentWorkspaceUI(mode);
  renderConversationList();
  renderConversation();
  if (state.user) await loadConversations(mode);
}

function selectInfraSource(source) {
  if (source === "live" && !state.capabilities?.infra_live_available) return;
  state.infraSource = source;
  $$(".infra-source-option").forEach((option) => {
    const selected = option.dataset.infraSource === source;
    option.classList.toggle("active", selected);
    option.setAttribute("aria-pressed", String(selected));
  });
  if (state.agentMode === "infra") updateAgentWorkspaceUI("infra");
}

function agentLabel(mode, infraSource = "snapshot") {
  if (mode === "infra" && infraSource === "live") return "LIVE INFRA AGENT";
  if (mode === "infra") return "INFRA AGENT";
  if (mode === "data") return "SQL REPORT AGENT";
  return "NEXUS AI";
}

async function loadConversations(mode = state.agentMode) {
  try {
    const conversations = await api(
      `/conversations?agent_mode=${encodeURIComponent(mode)}`,
    );
    state.conversationsByAgent[mode] = conversations;
    const active = state.activeConversationByAgent[mode];
    if (
      active
      && !conversations.some((conversation) => conversation.id === active.id)
    ) {
      state.activeConversationByAgent[mode] = null;
    }
    if (state.agentMode === mode) {
      state.activeConversation = state.activeConversationByAgent[mode];
      renderConversationList();
      renderConversation();
    }
  } catch (error) {
    if (error.status === 401) return logout(false);
    toast(error.message, "error");
  }
}

function renderConversationList() {
  const list = $("#conversation-list");
  list.replaceChildren();
  const conversations = conversationsFor();
  $("#conversation-count").textContent = conversations.length;
  for (const conversation of conversations) {
    const button = document.createElement("button");
    button.className = "conversation-item";
    if (state.activeConversation?.id === conversation.id) button.classList.add("active");
    const title = document.createElement("strong");
    title.textContent = conversation.title;
    const meta = document.createElement("small");
    meta.textContent = `${messageCountLabel(conversation.message_count)} · ${formatDate(conversation.updated_at)}`;
    button.append(title, meta);
    button.addEventListener("click", () => openConversation(conversation.id));
    list.appendChild(button);
  }
}

async function createConversation(
  title = agentWorkspaces()[state.agentMode].newChatLabel,
) {
  const mode = state.agentMode;
  const conversation = await api("/conversations", {
    method: "POST",
    body: JSON.stringify({ title, agent_mode: mode }),
  });
  state.conversationsByAgent[mode].unshift({
    ...conversation,
    message_count: 0,
  });
  const active = { ...conversation, messages: [] };
  state.activeConversationByAgent[mode] = active;
  if (state.agentMode === mode) {
    state.activeConversation = active;
    renderConversationList();
    renderConversation();
  }
  closeSidebar();
  $("#message-input").focus();
  return active;
}

async function openConversation(id) {
  const requestedMode = state.agentMode;
  try {
    const conversation = await api(`/conversations/${id}`);
    const mode = conversation.agent_mode || requestedMode;
    state.activeConversationByAgent[mode] = conversation;
    if (state.agentMode !== mode) {
      await selectAgent(mode);
    } else {
      state.activeConversation = conversation;
      renderConversationList();
      renderConversation();
    }
    switchView("chat");
    closeSidebar();
  } catch (error) {
    toast(error.message, "error");
  }
}

function renderConversation() {
  const active = state.activeConversation;
  show($("#empty-state"), !active);
  show($("#conversation-stage"), Boolean(active));
  show($("#delete-chat-button"), Boolean(active));
  if (!active) {
    $("#messages").replaceChildren();
    return;
  }
  $("#conversation-title").textContent = active.title;
  $("#message-count").textContent = messageCountLabel(active.messages.length).toUpperCase();
  const container = $("#messages");
  container.replaceChildren();
  active.messages.forEach((message) => container.appendChild(messageNode(message)));
  requestAnimationFrame(() => {
    container.scrollTop = container.scrollHeight;
  });
}

function appendInlineText(parent, text) {
  const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*)/g;
  let cursor = 0;
  for (const match of text.matchAll(pattern)) {
    parent.append(document.createTextNode(text.slice(cursor, match.index)));
    const token = match[0];
    const node = document.createElement(token.startsWith("`") ? "code" : "strong");
    node.textContent = token.startsWith("`") ? token.slice(1, -1) : token.slice(2, -2);
    parent.appendChild(node);
    cursor = match.index + token.length;
  }
  parent.append(document.createTextNode(text.slice(cursor)));
}

function markdownTableCells(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isMarkdownTableDivider(line) {
  const cells = markdownTableCells(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function richBlockStart(lines, index) {
  const line = lines[index] || "";
  return (
    !line.trim()
    || /^```/.test(line.trim())
    || /^#{1,3}\s+/.test(line)
    || /^\s*([-*]|\d+[.)])\s+/.test(line)
    || /^>\s?/.test(line)
    || (line.includes("|") && isMarkdownTableDivider(lines[index + 1] || ""))
  );
}

function renderRichText(container, text) {
  container.classList.add("message__content--rich");
  const lines = String(text).replace(/\r\n?/g, "\n").split("\n");
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.trim().match(/^```([\w-]*)/);
    if (fence) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = codeLines.join("\n");
      if (fence[1]) code.dataset.language = fence[1];
      pre.appendChild(code);
      container.appendChild(pre);
      continue;
    }

    if (line.includes("|") && isMarkdownTableDivider(lines[index + 1] || "")) {
      const headings = markdownTableCells(line);
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
        rows.push(markdownTableCells(lines[index]));
        index += 1;
      }
      const wrap = document.createElement("div");
      wrap.className = "message-table-wrap";
      const table = document.createElement("table");
      const thead = document.createElement("thead");
      const headingRow = document.createElement("tr");
      for (const heading of headings) {
        const cell = document.createElement("th");
        appendInlineText(cell, heading);
        headingRow.appendChild(cell);
      }
      thead.appendChild(headingRow);
      const tbody = document.createElement("tbody");
      for (const row of rows) {
        const tableRow = document.createElement("tr");
        for (let cellIndex = 0; cellIndex < headings.length; cellIndex += 1) {
          const cell = document.createElement("td");
          appendInlineText(cell, row[cellIndex] || "");
          tableRow.appendChild(cell);
        }
        tbody.appendChild(tableRow);
      }
      table.append(thead, tbody);
      wrap.appendChild(table);
      container.appendChild(wrap);
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    const reportTitle =
      container.childElementCount === 0 && /^REPORT\s*\//i.test(line.trim());
    if (heading || reportTitle) {
      const level = reportTitle ? 3 : Math.min(5, heading[1].length + 2);
      const node = document.createElement(`h${level}`);
      appendInlineText(node, reportTitle ? line.trim() : heading[2].trim());
      container.appendChild(node);
      index += 1;
      continue;
    }

    const listItem = line.match(/^\s*([-*]|\d+[.)])\s+(.+)$/);
    if (listItem) {
      const ordered = /^\d/.test(listItem[1]);
      const list = document.createElement(ordered ? "ol" : "ul");
      while (index < lines.length) {
        const item = lines[index].match(/^\s*([-*]|\d+[.)])\s+(.+)$/);
        if (!item || /^\d/.test(item[1]) !== ordered) break;
        const node = document.createElement("li");
        appendInlineText(node, item[2]);
        list.appendChild(node);
        index += 1;
      }
      container.appendChild(list);
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quote = document.createElement("blockquote");
      const quoteLines = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      appendInlineText(quote, quoteLines.join("\n"));
      container.appendChild(quote);
      continue;
    }

    const paragraphLines = [line];
    index += 1;
    while (index < lines.length && !richBlockStart(lines, index)) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    const paragraph = document.createElement("p");
    appendInlineText(paragraph, paragraphLines.join("\n"));
    container.appendChild(paragraph);
  }
}

function messageNode(message) {
  const article = document.createElement("article");
  article.className = `message message--${message.role}`;
  article.dataset.agentMode = message.agent_mode || "general";
  const avatar = document.createElement("div");
  avatar.className = "message__avatar";
  avatar.textContent = message.role === "assistant" ? "NX" : state.user.name.charAt(0).toUpperCase();
  const body = document.createElement("div");
  const head = document.createElement("div");
  head.className = "message__head";
  const author = document.createElement("strong");
  const infraSource = message.sources?.find(
    (source) => source.type === "infra",
  );
  author.textContent = message.role === "assistant"
    ? agentLabel(message.agent_mode, infraSource?.mode)
    : state.user.name.toUpperCase();
  const meta = document.createElement("span");
  meta.textContent = message.model
    ? `${message.model} · ${formatTime(message.created_at)}`
    : formatTime(message.created_at);
  head.append(author, meta);
  const content = document.createElement("div");
  content.className = "message__content";
  if (message.role === "assistant") {
    renderRichText(content, message.content);
  } else {
    content.textContent = message.content;
  }
  body.append(head, content);
  if (message.sources?.length) {
    const sources = document.createElement("div");
    sources.className = "message__sources";
    for (const source of message.sources) {
      const chip = document.createElement("span");
      if (source.type === "sql") {
        chip.classList.add("source-sql");
        const shortened = source.truncated || source.cells_truncated ? t("shortened") : "";
        chip.textContent = `SQL · ${source.row_count} ${t("rows")} · ${source.elapsed_ms} ms${shortened}`;
        const details = document.createElement("details");
        details.className = "message__sql";
        const summary = document.createElement("summary");
        summary.textContent = t("showSql");
        const query = document.createElement("code");
        query.textContent = source.query || t("sqlUnavailable");
        details.append(summary, query);
        sources.append(chip, details);
      } else if (source.type === "infra") {
        chip.classList.add(
          source.mode === "live" ? "source-infra-live" : "source-infra-snapshot",
        );
        chip.textContent = source.mode === "live"
          ? `● LIVE SERVER · ${formatDateTime(source.generated_at)}`
          : `SNAPSHOT · ${formatDateTime(source.generated_at)}`;
        sources.appendChild(chip);
      } else {
        chip.textContent = `KB · ${source.document} #${source.chunk}`;
        sources.appendChild(chip);
      }
    }
    body.appendChild(sources);
  }
  article.append(avatar, body);
  return article;
}

function typingNode(mode, infraSource) {
  const article = document.createElement("article");
  article.id = "typing-message";
  article.className = "message message--assistant";
  article.setAttribute("role", "status");
  article.setAttribute(
    "aria-label",
    t("preparing", { agent: agentLabel(mode, infraSource) }),
  );
  article.innerHTML = `
    <div class="message__avatar">NX</div>
    <div>
      <div class="message__head"><strong>${agentLabel(mode, infraSource)}</strong><span>${t("thinking")}</span></div>
      <div class="typing"><span></span><span></span><span></span></div>
    </div>`;
  return article;
}

async function sendMessage(content) {
  if (!content.trim() || state.sending) return;
  const mode = state.agentMode;
  const infraSource = mode === "infra" ? state.infraSource : "snapshot";
  let conversation = state.activeConversationByAgent[mode];
  if (!conversation) {
    const title = content.trim().slice(0, 62);
    conversation = await createConversation(
      title.length < content.trim().length ? `${title}…` : title,
    );
  }
  state.sending = true;
  $("#send-button").disabled = true;
  $("#composer").setAttribute("aria-busy", "true");
  const optimistic = {
    id: `temp-${Date.now()}`,
    role: "user",
    content: content.trim(),
    agent_mode: mode,
    created_at: new Date().toISOString(),
  };
  conversation.messages.push(optimistic);
  if (state.agentMode === mode) {
    renderConversation();
    $("#messages").appendChild(typingNode(mode, infraSource));
    $("#messages").scrollTop = $("#messages").scrollHeight;
  }
  try {
    const result = await api(`/conversations/${conversation.id}/messages`, {
      method: "POST",
      body: JSON.stringify({
        content: content.trim(),
        agent_mode: mode,
        infra_source: infraSource,
      }),
    });
    conversation.messages = conversation.messages.filter(
      (message) => message.id !== optimistic.id,
    );
    conversation.messages.push(result.user, result.assistant);
    const summary = conversationsFor(mode).find(
      (item) => item.id === conversation.id,
    );
    if (summary) {
      summary.message_count = conversation.messages.length;
      summary.updated_at = result.assistant.created_at;
    }
    if (state.agentMode === mode) {
      state.activeConversation = conversation;
      renderConversationList();
      renderConversation();
    }
  } catch (error) {
    conversation.messages = conversation.messages.filter(
      (message) => message.id !== optimistic.id,
    );
    if (state.agentMode === mode) renderConversation();
    toast(error.message, "error");
  } finally {
    state.sending = false;
    $("#send-button").disabled = false;
    $("#composer").setAttribute("aria-busy", "false");
    $("#message-input").focus();
  }
}

async function deleteActiveConversation() {
  if (!state.activeConversation) return;
  const mode = state.agentMode;
  const conversation = state.activeConversation;
  if (!window.confirm(t("conversationDeletePrompt", { title: conversation.title }))) return;
  try {
    await api(`/conversations/${conversation.id}`, { method: "DELETE" });
    state.conversationsByAgent[mode] = conversationsFor(mode).filter(
      (item) => item.id !== conversation.id,
    );
    state.activeConversationByAgent[mode] = null;
    state.activeConversation = null;
    renderConversationList();
    renderConversation();
    toast(t("conversationDeleted"));
  } catch (error) {
    toast(error.message, "error");
  }
}

function switchView(view) {
  state.activeView = view;
  show($("#chat-view"), view === "chat");
  show($("#admin-view"), view === "admin");
  $("#current-section").textContent = view === "admin"
    ? "CONTROL PLANE"
    : agentWorkspaces()[state.agentMode].sectionLabel;
  $$(".nav-item").forEach((item) => {
    const selected = item.dataset.view === view;
    item.classList.toggle("active", selected);
    if (selected) {
      item.setAttribute("aria-current", "page");
    } else {
      item.removeAttribute("aria-current");
    }
  });
  if (view === "admin") loadAdmin();
}

async function loadAdmin() {
  if (state.user?.role !== "admin") return;
  $("#admin-view").setAttribute("aria-busy", "true");
  try {
    const [overview, users, settings, rag, infra, dataSchema] = await Promise.all([
      api("/admin/overview"),
      api("/admin/users"),
      api("/admin/settings"),
      api("/admin/rag/documents"),
      api("/admin/infra/status"),
      api("/admin/data/schema"),
    ]);
    $("#metric-users").textContent = overview.users_total;
    $("#metric-active").textContent = overview.users_active;
    $("#metric-chats").textContent = overview.conversations_total;
    $("#metric-messages").textContent = overview.messages_total;
    $("#users-status").textContent = t("accountsCount", { count: users.length });
    renderUsers(users);
    $("#settings-model").value = settings.model;
    $("#settings-prompt").value = settings.system_prompt;
    $("#rag-enabled").checked = settings.rag_enabled;
    $("#rag-max-chunks").value = settings.rag_max_chunks;
    $("#infra-enabled").checked = settings.infra_agent_enabled;
    $("#infra-admin-only").checked = settings.infra_agent_admin_only;
    $("#infra-live-enabled").checked = settings.infra_live_enabled;
    $("#infra-model").value = settings.infra_model;
    $("#data-enabled").checked = settings.data_agent_enabled;
    $("#data-admin-only").checked = settings.data_agent_admin_only;
    $("#data-model").value = settings.data_model;
    $("#sidebar-model").textContent = settings.model;
    $("#api-status").textContent = settings.api_configured ? "API ONLINE" : "API MISSING";
    $("#api-status").style.color = settings.api_configured ? "var(--mint)" : "var(--danger)";
    renderDocuments(rag.documents);
    renderInfraStatus(infra);
    renderDataSchema(dataSchema.schema);
    loadModelCatalog();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    $("#admin-view").setAttribute("aria-busy", "false");
  }
}

function renderDataSchema(schema) {
  const container = $("#data-schema-tables");
  container.replaceChildren();
  const tableLines = schema
    .split("\n")
    .filter((line) => /^[a-z_]+\(/.test(line));
  for (const line of tableLines) {
    const open = line.indexOf("(");
    const chip = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = line.slice(0, open);
    const columns = document.createElement("small");
    columns.textContent = line.slice(open + 1, -1)
      .split(", ")
      .map((column) => column.split(" ")[0])
      .join(" · ");
    chip.append(name, columns);
    container.appendChild(chip);
  }
}

async function loadModelCatalog() {
  try {
    const result = await api("/admin/models");
    state.models = result.models;
    const datalist = $("#model-catalog");
    datalist.replaceChildren();
    for (const model of state.models) {
      const option = document.createElement("option");
      option.value = model.id;
      option.label = model.name;
      datalist.appendChild(option);
    }
    updateModelMeta();
  } catch (error) {
    $("#model-meta").textContent = t("catalogUnavailable");
  }
}

function updateModelMeta() {
  const selected = state.models.find((model) => model.id === $("#settings-model").value);
  if (!selected) {
    $("#model-meta").textContent = t("catalogCount", { count: state.models.length });
    return;
  }
  const context = selected.context_length
    ? `${Math.round(selected.context_length / 1000)}k ${t("context")}`
    : t("contextUnknown");
  const inputPrice = Number(selected.prompt_price || 0) * 1_000_000;
  const outputPrice = Number(selected.completion_price || 0) * 1_000_000;
  $("#model-meta").textContent =
    `${selected.name} · ${context} · ${formatUsd(inputPrice)}/${formatUsd(outputPrice)} ${t("perMillionTokens")}`;
}

function renderDocuments(documents) {
  const container = $("#rag-documents");
  container.replaceChildren();
  if (!documents.length) {
    const empty = document.createElement("p");
    empty.className = "document-empty";
    empty.textContent = t("noDocuments");
    container.appendChild(empty);
    return;
  }
  for (const documentData of documents) {
    const row = document.createElement("div");
    row.className = "document-row";
    const info = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = documentData.name;
    const meta = document.createElement("small");
    meta.textContent = t("passages", {
      count: documentData.chunk_count,
      chars: Math.ceil(documentData.character_count / 1000),
    });
    info.append(name, meta);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = t("remove");
    remove.setAttribute("aria-label", t("removeDocumentLabel", { name: documentData.name }));
    remove.addEventListener("click", () => deleteRagDocument(documentData.id));
    row.append(info, remove);
    container.appendChild(row);
  }
}

function renderInfraStatus(status) {
  const container = $("#infra-snapshot-status");
  container.classList.toggle("online", status.available);
  container.querySelector("strong").textContent = status.available
    ? `SNAPSHOT ${formatDateTime(status.generated_at)}`
    : t("snapshotUnavailable");
}

async function uploadRagDocuments(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  if (state.ragUploading) {
    toast(t("uploadInProgress"), "error");
    return;
  }
  if (files.length > RAG_MAX_FILES_PER_BATCH) {
    toast(t("tooManyFiles", { count: RAG_MAX_FILES_PER_BATCH }), "error");
    $("#rag-file").value = "";
    return;
  }
  const oversized = files.find((file) => file.size > RAG_MAX_FILE_BYTES);
  if (oversized) {
    toast(t("fileTooLarge", { name: oversized.name }), "error");
    $("#rag-file").value = "";
    return;
  }
  const totalBytes = files.reduce((total, file) => total + file.size, 0);
  if (totalBytes > RAG_MAX_BATCH_BYTES) {
    toast(t("batchTooLarge"), "error");
    $("#rag-file").value = "";
    return;
  }

  const drop = $("#rag-drop");
  const status = $("#rag-upload-status");
  const queue = [...files];
  const failures = [];
  let completed = 0;
  state.ragUploading = true;
  drop.classList.add("uploading");
  status.textContent = t("uploading", { done: 0, total: files.length });

  async function worker() {
    while (queue.length) {
      const file = queue.shift();
      try {
        await api("/admin/rag/documents", {
          method: "POST",
          body: JSON.stringify({ name: file.name, content: await file.text() }),
        });
      } catch (error) {
        failures.push({ name: file.name, message: error.message });
      } finally {
        completed += 1;
        status.textContent = t("uploading", { done: completed, total: files.length });
      }
    }
  }

  try {
    await Promise.all(
      Array.from(
        { length: Math.min(RAG_UPLOAD_CONCURRENCY, files.length) },
        () => worker(),
      ),
    );
    const succeeded = files.length - failures.length;
    status.textContent = failures.length
      ? t("uploadPartial", { success: succeeded, failed: failures.length })
      : t("uploadDone", { count: succeeded });
    if (failures.length) {
      toast(`${failures[0].name}: ${failures[0].message}`, "error");
    } else {
      toast(t("filesAdded", { count: succeeded }));
    }
    renderDocuments((await api("/admin/rag/documents")).documents);
  } finally {
    state.ragUploading = false;
    $("#rag-file").value = "";
    drop.classList.remove("uploading", "dragging");
  }
}

async function deleteRagDocument(id) {
  if (!window.confirm(t("removeDocumentPrompt"))) return;
  try {
    await api(`/admin/rag/documents/${id}`, { method: "DELETE" });
    renderDocuments((await api("/admin/rag/documents")).documents);
    toast(t("documentRemoved"));
  } catch (error) {
    toast(error.message, "error");
  }
}

function renderUsers(users) {
  const tbody = $("#users-table");
  tbody.replaceChildren();
  for (const user of users) {
    const row = document.createElement("tr");
    const identity = document.createElement("td");
    identity.dataset.label = t("account");
    identity.innerHTML = `<div class="user-cell"><span class="avatar"></span><span><strong></strong><small></small></span></div>`;
    identity.querySelector(".avatar").textContent = user.name.charAt(0).toUpperCase();
    identity.querySelector("strong").textContent = user.name;
    identity.querySelector("small").textContent = user.username
      ? t("loginPrefix", { name: user.username })
      : user.email;

    const roleCell = document.createElement("td");
    roleCell.dataset.label = t("role");
    const role = document.createElement("select");
    role.className = "role-select";
    role.innerHTML = '<option value="user">USER</option><option value="admin">ADMIN</option>';
    role.value = user.role;
    role.setAttribute("aria-label", t("userRoleLabel", { name: user.name }));
    role.disabled = user.id === state.user.id;
    role.addEventListener("change", () => updateUser(user.id, { role: role.value }));
    roleCell.appendChild(role);

    const statusCell = document.createElement("td");
    statusCell.dataset.label = t("status");
    const statusButton = document.createElement("button");
    statusButton.className = `status-toggle ${user.is_active ? "active" : "disabled"}`;
    statusButton.textContent = user.is_active ? "● ACTIVE" : "○ DISABLED";
    statusButton.setAttribute(
      "aria-label",
      t(user.is_active ? "deactivateUser" : "activateUser", { name: user.name }),
    );
    statusButton.disabled = user.id === state.user.id;
    statusButton.addEventListener("click", () =>
      updateUser(user.id, { is_active: !user.is_active }),
    );
    statusCell.appendChild(statusButton);

    const created = document.createElement("td");
    created.dataset.label = t("created");
    created.textContent = formatDate(user.created_at);
    row.append(identity, roleCell, statusCell, created);
    tbody.appendChild(row);
  }
}

async function updateUser(id, changes) {
  try {
    await api(`/admin/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
    toast(t("userUpdated"));
    loadAdmin();
  } catch (error) {
    toast(error.message, "error");
    loadAdmin();
  }
}

async function createAdminUser(form) {
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const data = new FormData(form);
    const created = await api("/admin/users", {
      method: "POST",
      body: JSON.stringify({
        name: data.get("name"),
        password: data.get("password"),
        role: data.get("role"),
      }),
    });
    form.reset();
    $("#admin-user-password-copy").disabled = true;
    toast(t("accountCreated", {
      role: created.role === "admin" ? t("administrator") : t("user"),
      name: created.name,
    }));
    await loadAdmin();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    button.disabled = false;
  }
}

function secureRandomIndex(length) {
  const values = new Uint32Array(1);
  const ceiling = Math.floor(0x100000000 / length) * length;
  do {
    crypto.getRandomValues(values);
  } while (values[0] >= ceiling);
  return values[0] % length;
}

function generateSecurePassword(length = 18) {
  const groups = [
    "ABCDEFGHJKLMNPQRSTUVWXYZ",
    "abcdefghijkmnopqrstuvwxyz",
    "23456789",
    "!@#$%*-_+",
  ];
  const alphabet = groups.join("");
  const characters = groups.map((group) => group[secureRandomIndex(group.length)]);
  while (characters.length < length) {
    characters.push(alphabet[secureRandomIndex(alphabet.length)]);
  }
  for (let index = characters.length - 1; index > 0; index -= 1) {
    const swapIndex = secureRandomIndex(index + 1);
    [characters[index], characters[swapIndex]] = [characters[swapIndex], characters[index]];
  }
  return characters.join("");
}

function generateAdminPassword() {
  const input = $("#admin-user-password");
  input.value = generateSecurePassword();
  $("#admin-user-password-copy").disabled = false;
  input.focus();
  input.select();
  toast(t("passwordGenerated"));
}

async function copyAdminPassword() {
  const input = $("#admin-user-password");
  if (!input.value) return;
  try {
    await navigator.clipboard.writeText(input.value);
    toast(t("passwordCopied"));
  } catch {
    input.focus();
    input.select();
    toast(t("passwordSelected"));
  }
}

function settingsPayload() {
  return {
    model: $("#settings-model").value.trim(),
    system_prompt: $("#settings-prompt").value.trim(),
    rag_enabled: $("#rag-enabled").checked,
    rag_max_chunks: Number($("#rag-max-chunks").value),
    infra_agent_enabled: $("#infra-enabled").checked,
    infra_agent_admin_only: $("#infra-admin-only").checked,
    infra_live_enabled: $("#infra-live-enabled").checked,
    infra_model: $("#infra-model").value.trim(),
    data_agent_enabled: $("#data-enabled").checked,
    data_agent_admin_only: $("#data-admin-only").checked,
    data_model: $("#data-model").value.trim(),
  };
}

async function saveSettings(form) {
  state.settingsQueued = true;
  if (state.settingsSaving) return;
  state.settingsSaving = true;
  const button = form.querySelector("button");
  button.dataset.originalLabel ||= button.textContent;
  button.textContent = t("saving");
  button.disabled = true;
  let savedSettings = null;
  let failure = null;
  try {
    while (state.settingsQueued) {
      state.settingsQueued = false;
      try {
        savedSettings = await api("/admin/settings", {
          method: "PUT",
          body: JSON.stringify(settingsPayload()),
        });
      } catch (error) {
        failure = error;
        state.settingsQueued = false;
      }
    }
  } finally {
    state.settingsSaving = false;
    button.textContent = button.dataset.originalLabel;
    button.disabled = false;
  }
  if (failure) {
    toast(failure.message, "error");
    await loadAdmin();
    return;
  }
  if (savedSettings) {
    $("#sidebar-model").textContent = savedSettings.model;
    await loadCapabilities();
    toast(t("settingsSaved"));
  }
}

async function logout(notify = true) {
  try {
    await api("/auth/logout", { method: "POST" });
  } catch {}
  state.user = null;
  state.activeConversation = null;
  state.conversationsByAgent = { general: [], infra: [], data: [] };
  state.activeConversationByAgent = {
    general: null,
    infra: null,
    data: null,
  };
  state.capabilities = null;
  state.infraSource = "snapshot";
  await selectAgent("general");
  closeSidebar();
  setUserMenu(false);
  $("#login-form").reset();
  $("#register-form").reset();
  show($("#workspace"), false);
  show($("#auth-view"));
  setAuthMode("login");
  if (notify) toast(t("loggedOut"));
}

function syncSidebarAccessibility() {
  const sidebar = $("#sidebar");
  const mobile = mobileSidebarQuery.matches;
  const open = mobile && sidebar.classList.contains("open");
  $("#sidebar-open").setAttribute("aria-expanded", String(open));
  $("#sidebar-scrim").setAttribute("aria-hidden", String(!open));
  if ("inert" in sidebar) sidebar.inert = mobile && !open;
  if ("inert" in $("#main-content")) $("#main-content").inert = open;
  if (mobile && !open) {
    sidebar.setAttribute("aria-hidden", "true");
  } else {
    sidebar.removeAttribute("aria-hidden");
  }
}

function openSidebar() {
  $("#sidebar").classList.add("open");
  show($("#sidebar-scrim"));
  syncSidebarAccessibility();
  requestAnimationFrame(() => $("#sidebar-close").focus());
}

function closeSidebar(restoreFocus = false) {
  const wasOpen = $("#sidebar").classList.contains("open");
  $("#sidebar").classList.remove("open");
  show($("#sidebar-scrim"), false);
  syncSidebarAccessibility();
  if (restoreFocus && wasOpen && mobileSidebarQuery.matches) {
    $("#sidebar-open").focus();
  }
}

function setUserMenu(open) {
  show($("#user-menu"), open);
  $("#user-menu-button").setAttribute("aria-expanded", String(open));
}

function bindEvents() {
  $$('[data-language]').forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.language));
  });
  $$(".auth-tab").forEach((tab, index, tabs) => {
    tab.addEventListener("click", () => setAuthMode(tab.dataset.authMode));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(index + direction + tabs.length) % tabs.length];
      setAuthMode(next.dataset.authMode);
      next.focus();
    });
  });
  $("#login-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitAuth(event.currentTarget, "login");
  });
  $("#register-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submitAuth(event.currentTarget, "register");
  });
  $("#new-chat-button").addEventListener("click", () => createConversation());
  $$(".nav-item").forEach((item) =>
    item.addEventListener("click", () => {
      switchView(item.dataset.view);
      closeSidebar(false);
    }),
  );
  $("#composer").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = $("#message-input");
    const content = input.value;
    if (!content.trim()) return;
    input.value = "";
    input.style.height = "auto";
    sendMessage(content);
  });
  $("#message-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      $("#composer").requestSubmit();
    }
  });
  $("#message-input").addEventListener("input", (event) => {
    event.target.style.height = "auto";
    event.target.style.height = `${Math.min(event.target.scrollHeight, 180)}px`;
  });
  $$(".prompt-card").forEach((card) =>
    card.addEventListener("click", () => {
      $("#message-input").value = card.dataset.prompt;
      $("#message-input").focus();
    }),
  );
  $("#delete-chat-button").addEventListener("click", deleteActiveConversation);
  $("#settings-form").addEventListener("submit", (event) => {
    event.preventDefault();
    saveSettings(event.currentTarget);
  });
  $("#admin-user-create-form").addEventListener("submit", (event) => {
    event.preventDefault();
    createAdminUser(event.currentTarget);
  });
  $("#admin-user-password-generate").addEventListener("click", generateAdminPassword);
  $("#admin-user-password-copy").addEventListener("click", copyAdminPassword);
  $("#admin-user-password").addEventListener("input", (event) => {
    $("#admin-user-password-copy").disabled = !event.target.value;
  });
  $$(".agent-option").forEach((option) =>
    option.addEventListener("click", () => selectAgent(option.dataset.agent)),
  );
  $$(".infra-source-option").forEach((option) =>
    option.addEventListener(
      "click",
      () => selectInfraSource(option.dataset.infraSource),
    ),
  );
  $("#settings-model").addEventListener("input", updateModelMeta);
  [
    "#rag-enabled",
    "#rag-max-chunks",
    "#infra-enabled",
    "#infra-admin-only",
    "#infra-live-enabled",
    "#data-enabled",
    "#data-admin-only",
  ].forEach(
    (selector) => $(selector).addEventListener("change", () => saveSettings($("#settings-form"))),
  );
  $("#rag-file").addEventListener("change", (event) =>
    uploadRagDocuments(event.target.files),
  );
  const ragDrop = $("#rag-drop");
  ["dragenter", "dragover"].forEach((eventName) =>
    ragDrop.addEventListener(eventName, (event) => {
      event.preventDefault();
      ragDrop.classList.add("dragging");
    }),
  );
  ["dragleave", "drop"].forEach((eventName) =>
    ragDrop.addEventListener(eventName, (event) => {
      event.preventDefault();
      ragDrop.classList.remove("dragging");
    }),
  );
  ragDrop.addEventListener("drop", (event) =>
    uploadRagDocuments(event.dataTransfer.files),
  );
  ragDrop.addEventListener("keydown", (event) => {
    if (!["Enter", " "].includes(event.key)) return;
    event.preventDefault();
    $("#rag-file").click();
  });
  $("#logout-button").addEventListener("click", () => logout());
  $("#user-menu-button").addEventListener("click", () =>
    setUserMenu($("#user-menu").classList.contains("hidden")),
  );
  $("#sidebar-open").addEventListener("click", openSidebar);
  $("#sidebar-close").addEventListener("click", () => closeSidebar(true));
  $("#sidebar-scrim").addEventListener("click", () => closeSidebar(true));
  mobileSidebarQuery.addEventListener("change", () => {
    if (!mobileSidebarQuery.matches) closeSidebar();
    syncSidebarAccessibility();
  });
  document.addEventListener("click", (event) => {
    if (
      !$("#user-menu").classList.contains("hidden")
      && !$("#user-menu").contains(event.target)
      && !$("#user-menu-button").contains(event.target)
    ) {
      setUserMenu(false);
    }
  });
  document.addEventListener("keydown", (event) => {
    if (
      event.key.toLowerCase() === "n"
      && !event.ctrlKey
      && !event.metaKey
      && !event.altKey
      && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)
      && state.user
    ) {
      createConversation();
    }
    if (event.key === "Escape") {
      closeSidebar(true);
      setUserMenu(false);
    }
  });
  syncSidebarAccessibility();
}

initialize();
