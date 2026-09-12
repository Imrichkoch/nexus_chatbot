const basePath = new URL('.', document.baseURI).pathname.replace(/\/$/, '');
const apiBase = `${basePath}/api`;
const RAG_MAX_FILES_PER_BATCH = 1000;
const RAG_MAX_FILE_BYTES = 10 * 1024 * 1024;
const RAG_MAX_BATCH_BYTES = 50 * 1024 * 1024;

const TRANSLATIONS = {
  infraServers: { en: 'Server connections', sk: 'Pripojenia serverov' },
  infraServerHelp: { en: 'Linux SSH, Windows SSH and Windows WinRM HTTPS use a fixed read-only collector without unrestricted shell access.', sk: 'Linux SSH, Windows SSH a Windows WinRM HTTPS používajú pevný read-only collector bez voľného prístupu k shellu.' },
  infraSavedServers: { en: 'Saved servers', sk: 'Uložené servery' },
  infraNewServer: { en: 'New server', sk: 'Nový server' },
  infraDeleteServer: { en: 'Delete server', sk: 'Vymazať server' },
  infraServerChat: { en: 'Server for this chat', sk: 'Server pre tento chat' },
  infraServerChatHelp: { en: 'Choosing another server starts a new chat. Existing chats keep their server.', sk: 'Výber iného servera otvorí nový chat. Existujúce chaty si ponechajú svoj server.' },
  infraConnectionName: { en: 'Connection name', sk: 'Názov pripojenia' },
  infraConnectionType: { en: 'Connection type', sk: 'Typ pripojenia' },
  infraPort: { en: 'Port', sk: 'Port' },
  infraUser: { en: 'Username', sk: 'Používateľské meno' },
  infraAuthentication: { en: 'Authentication', sk: 'Autentifikácia' },
  infraWinrmPassword: { en: 'WinRM password', sk: 'WinRM heslo' },
  infraPasswordNew: { en: 'Required for a new connection.', sk: 'Povinné pre nové pripojenie.' },
  infraPasswordKeep: { en: 'Leave blank to keep the saved password.', sk: 'Prázdne pole ponechá uložené heslo.' },
  infraCaFile: { en: 'CA certificate filename (optional)', sk: 'Názov CA certifikátu (voliteľné)' },
  infraCaHelp: { en: 'Filename inside NEXUS_INFRA_CA_ROOT. Certificate and hostname verification cannot be disabled.', sk: 'Názov súboru v NEXUS_INFRA_CA_ROOT. Overenie certifikátu a hostname nemožno vypnúť.' },
  infraSshPort: { en: 'SSH port', sk: 'SSH port' },
  infraSshUser: { en: 'SSH username', sk: 'SSH používateľ' },
  infraIdentity: { en: 'Approved identity filename', sk: 'Názov schváleného kľúča' },
  infraIdentityHelp: { en: 'Filename inside NEXUS_INFRA_SSH_KEY_ROOT; paths are rejected.', sk: 'Názov súboru v NEXUS_INFRA_SSH_KEY_ROOT; cesty sú odmietnuté.' },
  infraTestLive: { en: 'Test LIVE', sk: 'Otestovať LIVE' },
  infraSaveServer: { en: 'Save server', sk: 'Uložiť server' },
  dbSavedConnections: { en: 'Saved connections', sk: 'Uložené pripojenia' },
  dbDefaultConnection: { en: 'Default connection', sk: 'Predvolené pripojenie' },
  dbNewConnection: { en: 'New connection', sk: 'Nové pripojenie' },
  dbDeleteConnection: { en: 'Delete connection', sk: 'Vymazať pripojenie' },
  dbConnectionName: { en: 'Connection name', sk: 'Názov pripojenia' },
  dbChatSource: { en: 'Database for this chat', sk: 'Databáza pre tento chat' },
  dbChatSourceHelp: { en: 'Choosing another database starts a new chat. Existing chats keep their source.', sk: 'Výber inej databázy otvorí nový chat. Existujúce chaty si ponechajú svoj zdroj.' },
  dbUnavailable: { en: 'Unavailable connection', sk: 'Nedostupné pripojenie' },
  dbDeleteConfirm: { en: 'Delete this saved connection? Connections used by chats cannot be deleted.', sk: 'Vymazať uložené pripojenie? Pripojenie používané v chatoch nemožno vymazať.' },
  dbProfileSaved: { en: 'Connection saved. Select it in Data chat.', sk: 'Pripojenie uložené. Vyber ho v Data chate.' },
  dbSaveConnection: { en: 'Save connection', sk: 'Uložiť pripojenie' },
  dbConnection: { en: 'Database connection', sk: 'Pripojenie databázy' },
  dbHelp: { en: 'Save named connections, then choose a database in each Data chat. Testing does not save changes. Existing chats keep their source.', sk: 'Ulož pomenované pripojenia a vyber databázu v každom Data chate. Test neukladá zmeny. Existujúce chaty si ponechajú svoj zdroj.' },
  dbType: { en: 'Database type', sk: 'Typ databázy' },
  dbDemo: { en: 'Demo — synthetic SQLite', sk: 'Demo — fiktívna SQLite' },
  dbSqlite: { en: 'SQLite — external file', sk: 'SQLite — externý súbor' },
  dbHost: { en: 'Hostname / IP', sk: 'Názov servera / IP' },
  dbPort: { en: 'Port', sk: 'Port' },
  dbName: { en: 'Database / Oracle service / SQLite filename', sk: 'Databáza / Oracle service / názov SQLite súboru' },
  dbSchema: { en: 'Schema (optional)', sk: 'Schéma (voliteľná)' },
  dbUser: { en: 'Database username', sk: 'Databázový používateľ' },
  dbPassword: { en: 'Database password', sk: 'Databázové heslo' },
  dbKeepPassword: { en: 'Leave blank to keep saved password', sk: 'Prázdne = ponechať uložené heslo' },
  dbTls: { en: 'Verify TLS certificate and hostname', sk: 'Overovať TLS certifikát a názov servera' },
  dbTables: { en: 'Allowed tables / views (comma-separated)', sk: 'Povolené tabuľky / pohľady (oddelené čiarkou)' },
  dbReadOnly: { en: 'I use a dedicated SELECT-only account, without write or administrative grants.', sk: 'Používam samostatný účet iba na SELECT, bez oprávnení na zápis a administráciu.' },
  dbEgress: { en: 'I approve sending selected schema and query results to the configured AI provider.', sk: 'Schvaľujem odosielanie zvolenej schémy a výsledkov dotazov nakonfigurovanému AI poskytovateľovi.' },
  dbBoundary: { en: 'Table selection is not a replacement for database permissions. External sources are restricted to Nexus administrators.', sk: 'Výber tabuliek nenahrádza databázové oprávnenia. Externé zdroje sú prístupné iba administrátorom Nexusu.' },
  dbTest: { en: 'Test and list tables', sk: 'Otestovať a zobraziť tabuľky' },
  dbSave: { en: 'Save and activate', sk: 'Uložiť a aktivovať' },
  dbSaved: { en: 'Database source activated.', sk: 'Databázový zdroj bol aktivovaný.' },
  dbTesting: { en: 'Connecting…', sk: 'Pripájam…' },
  dbTablesFound: { en: 'Connection verified. Available tables/views:', sk: 'Spojenie overené. Dostupné tabuľky/pohľady:' },
  dbSqliteNote: { en: 'SQLite: place the file in the server directory NEXUS_EXTERNAL_SQLITE_ROOT. Enter only its filename. No upload or file creation occurs here.', sk: 'SQLite: vlož súbor do serverového adresára NEXUS_EXTERNAL_SQLITE_ROOT. Zadaj iba názov súboru. Tu sa súbory nenahrávajú ani nevytvárajú.' },
  dbMssqlNote: { en: 'SQL Server requires Microsoft ODBC Driver 18 on the application server. ApplicationIntent is not a permission boundary; use SELECT-only grants.', sk: 'SQL Server vyžaduje Microsoft ODBC Driver 18 na aplikačnom serveri. ApplicationIntent nenahrádza oprávnenia; účet musí mať iba SELECT.' },
  dbNetworkNote: { en: 'The Nexus server must reach this database. TLS verification is required by default; a corporate CA can be configured by the operator.', sk: 'Server Nexusu musí mať prístup k databáze. Predvolene je povinné overovanie TLS; firemnú CA môže nastaviť správca servera.' },
  dbSchemaTitle: { en: 'Active reporting schema', sk: 'Aktívna reportovacia schéma' },
  dbLimits: { en: 'SELECT/WITH · max 100 rows · external sources are admin-only', sk: 'SELECT/WITH · max 100 riadkov · externé zdroje iba pre adminov' },
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
  unsavedChanges: { en: "UNSAVED CHANGES", sk: "NEULOŽENÉ ZMENY" },
  unsavedChangesCopy: { en: "Review and save the configuration before leaving this session.", sk: "Skontroluj a ulož konfiguráciu pred ukončením tejto relácie." },
  discardChanges: { en: "Discard", sk: "Zahodiť" },
  discardChangesPrompt: { en: "Discard unsaved configuration changes?", sk: "Zahodiť neuložené zmeny konfigurácie?" },
  ragToggle: { en: "Enable or disable RAG", sk: "Zapnúť alebo vypnúť RAG" },
  ragCopy: { en: "Local knowledge base. Relevant passages are attached to the question and sources are shown with the answer.", sk: "Lokálna znalostná báza. Relevantné pasáže sa pripájajú k otázke a v odpovedi sa zobrazia zdroje." },
  maxPassages: { en: "Max. passages", sk: "Max. počet pasáží" },
  ragCapacity: { en: '{count}/{max} documents in the knowledge base', sk: '{count}/{max} dokumentov v znalostnej báze' },
  addFiles: { en: "＋ ADD OR DROP FILES", sk: "＋ PRIDAŤ ALEBO PRETIAHNUŤ SÚBORY" },
  fileLimits: { en: "TXT, MD, JSON, YAML, CSV, or LOG · max 1000 at once · 10 MB/file · 50 MB/batch", sk: "TXT, MD, JSON, YAML, CSV alebo LOG · max 1000 naraz · 10 MB/súbor · 50 MB/dávka" },
  infraToggle: { en: "Enable or disable Infra Agent", sk: "Zapnúť alebo vypnúť Infra Agenta" },
  infraCopy: { en: "Switchable one-minute snapshot or LIVE read-only check. It has no unrestricted shell and cannot change the server.", sk: "Prepínateľný minútový snapshot alebo LIVE read-only kontrola. Nemá voľný shell a nevie meniť server." },
  snapshotUnavailable: { en: "SNAPSHOT UNAVAILABLE", sk: "SNAPSHOT NEDOSTUPNÝ" },
  adminsOnly: { en: "Administrators only", sk: "Iba administrátori" },
  allowLive: { en: "Allow LIVE for admins", sk: "Povoliť LIVE adminom" },
  infraBoundary: { en: "CPU · RAM · disk · ports · TLS · health · approved systemd services", sk: "CPU · RAM · disk · porty · TLS · health · povolené systemd služby" },
  dataToggle: { en: "Enable or disable SQL Report Agent", sk: "Zapnúť alebo vypnúť SQL Report Agenta" },
  dataCopy: { en: 'Turns questions into read-only SQL and reports over the selected database source.', sk: 'Mení otázky na read-only SQL a reporty nad zvoleným databázovým zdrojom.' },
  syntheticBoundary: { en: "No real accounts or chats · SELECT/WITH · max 100 rows · time limit", sk: "Žiadne reálne účty ani chaty · SELECT/WITH · max 100 riadkov · časový limit" },
  fictionalSchema: { en: "Fictional schema", sk: "Fiktívna schéma" },
  tryAsking: { en: "TRY ASKING", sk: "SKÚS SA OPÝTAŤ" },
  exampleSales: { en: "“Compare revenue by country and segment.”", sk: "„Porovnaj tržby podľa krajín a segmentov.“" },
  exampleMargin: { en: "“Which products have the highest margin?”", sk: "„Ktoré produkty majú najvyššiu maržu?“" },
  exampleSla: { en: "“Create an SLA report for support tickets.”", sk: "„Sprav SLA report support ticketov.“" },
  ldapIntegration: { en: "LDAP integration", sk: "LDAP integrácia" },
  ldapToggle: { en: "Enable or disable LDAP sign-in", sk: "Zapnúť alebo vypnúť LDAP prihlásenie" },
  ldapCopy: { en: "Connect a company directory for user sign-in. Local accounts remain available and LDAP never creates an administrator automatically.", sk: "Pripojenie firemného adresára pre používateľské prihlásenie. Lokálne účty zostávajú funkčné a LDAP nikdy automaticky nevytvorí administrátora." },
  bindPassword: { en: "Bind password", sk: "Bind heslo" },
  bindPasswordPlaceholder: { en: "Leave blank to keep the saved password", sk: "Prázdne pole ponechá uložené heslo" },
  userFilter: { en: "User filter", sk: "Filter používateľa" },
  nameAttribute: { en: "Name attribute", sk: "Atribút mena" },
  emailAttribute: { en: "E-mail attribute", sk: "Atribút e-mailu" },
  verifyTls: { en: "Verify TLS certificate", sk: "Overovať TLS certifikát" },
  startTls: { en: 'StartTLS for ldap://', sk: 'StartTLS pre ldap://' },
  autoProvision: { en: "Automatically create a USER account after first sign-in", sk: "Automaticky vytvoriť USER účet po prvom prihlásení" },
  clearBindPassword: { en: "Remove saved bind password", sk: "Odstrániť uložené bind heslo" },
  ldapBoundary: { en: "The bind password is stored outside the database with service-only permissions and is never sent back to the browser.", sk: "Bind heslo sa ukladá mimo databázy s oprávnením iba pre službu a nikdy sa neposiela späť do prehliadača." },
  testConnection: { en: "Test connection", sk: "Otestovať spojenie" },
  saveLdap: { en: "Save LDAP", sk: "Uložiť LDAP" },
  ldapDisabled: { en: "LDAP DISABLED", sk: "LDAP VYPNUTÉ" },
  ldapReady: { en: "LDAP CONFIGURED", sk: "LDAP NAKONFIGUROVANÉ" },
  ldapSaved: { en: "LDAP configuration saved.", sk: "LDAP konfigurácia bola uložená." },
  ldapTesting: { en: "Testing…", sk: "Testujem…" },
  ldapConnected: { en: "LDAP connection is working.", sk: "LDAP spojenie funguje." },
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
  settingsDirty: false,
  ldapDirty: false,
  ldapBusy: false,
  dbDirty: false,
  dbBusy: false,
  dbRevision: 0,
  dbProfileId: 'default',
  dbProfiles: [],
  dbDefaultSettings: null,
  databaseChoices: [],
  selectedDatabaseId: null,
  infraProfiles: [],
  infraProfileId: 'new',
  infraRevision: 0,
  infraDirty: false,
  infraBusy: false,
  infraChoices: [],
  selectedInfraId: null,
  ragUploading: false,
  ragMaxDocuments: 1000,
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
    emptyEyebrow: "DATA AGENT / READ-ONLY DB",
    emptyTitleLead: "Aký report",
    emptyTitleAccent: "pripravíme?",
    emptyDescription: "Samostatný priestor pre read-only SQL a reporty zo zvolenej databázy.",
    placeholder: "Požiadaj o report alebo napíš read-only SQL…",
    disclaimer: "Data Agent číta zvolenú databázu. Externé zdroje sú iba pre adminov; výsledky sa odosielajú AI poskytovateľovi.",
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
    emptyEyebrow: "DATA AGENT / READ-ONLY DB",
    emptyTitleLead: "Which report",
    emptyTitleAccent: "shall we prepare?",
    emptyDescription: "A separate workspace for read-only SQL and reports over the selected database.",
    placeholder: "Request a report or enter read-only SQL…",
    disclaimer: "Data Agent reads the configured database. External sources are admin-only; results are sent to the AI provider.",
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
  databaseFieldsVisibility();
  renderDatabaseProfiles();
  renderInfraProfiles();
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

async function streamApi(path, options, onEvent) {
  const response = await fetch(`${apiBase}${path}`, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "Accept-Language": state.language,
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.detail || t("requestFailed"));
    error.status = response.status;
    throw error;
  }
  if (!response.body) throw new Error(t("requestFailed"));

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (line.trim()) onEvent(JSON.parse(line));
    }
    if (done) break;
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer));
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
    const config = await api('/auth/config');
    show($('[data-auth-mode="register"]'), config.registration_enabled);
  } catch (error) {
    show($('[data-auth-mode="register"]'), false);
  }
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
    const sources = await api('/data/connections');
    const infraSources = await api('/infra/connections');
    state.databaseChoices = sources.connections;
    state.selectedDatabaseId ||= sources.default_id;
    renderDatabaseChooser();
    state.infraChoices = infraSources.connections;
    state.selectedInfraId ||= infraSources.default_id;
    renderInfraServerChooser();
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
  renderDatabaseChooser();
  renderInfraServerChooser();
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
    body: JSON.stringify({ title, agent_mode: mode,
      ...(mode === 'data' ? { database_connection_id: state.selectedDatabaseId } : {}),
      ...(mode === 'infra' ? { infra_connection_id: state.selectedInfraId } : {}),
    }),
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
  renderDatabaseChooser();
  renderInfraServerChooser();
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
        const server = source.server ? ` · ${source.server}` : '';
        chip.textContent = source.mode === "live"
          ? `● LIVE SERVER${server} · ${formatDateTime(source.generated_at)}`
          : `SNAPSHOT${server} · ${formatDateTime(source.generated_at)}`;
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
  state.sending = true;
  $('#send-button').disabled = true;
  const mode = state.agentMode;
  const infraSource = mode === "infra" ? state.infraSource : "snapshot";
  let conversation = state.activeConversationByAgent[mode];
  if (!conversation) {
    const title = content.trim().slice(0, 62);
    try {
      conversation = await createConversation(
        title.length < content.trim().length ? `${title}…` : title,
      );
    } catch (error) {
      state.sending = false;
      $('#send-button').disabled = false;
      $('#message-input').value = content;
      toast(error.message, 'error');
      return;
    }
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
    let result = null;
    let streamedContent = "";
    let streamingArticle = null;
    await streamApi(`/conversations/${conversation.id}/messages/stream`, {
      method: "POST",
      body: JSON.stringify({
        content: content.trim(),
        agent_mode: mode,
        infra_source: infraSource,
      }),
    }, (event) => {
      if (event.type === "error") throw new Error(event.detail || t("requestFailed"));
      if (event.type === "done") {
        result = event;
        return;
      }
      if (event.type !== "delta" || !event.content) return;
      streamedContent += event.content;
      if (state.agentMode !== mode) return;
      if (!streamingArticle) {
        document.querySelector("#typing-message")?.remove();
        streamingArticle = messageNode({
          role: "assistant",
          content: "",
          agent_mode: mode,
          created_at: new Date().toISOString(),
          sources: [],
        });
        streamingArticle.id = "streaming-message";
        streamingArticle.setAttribute("aria-live", "polite");
        $("#messages").appendChild(streamingArticle);
      }
      streamingArticle.querySelector(".message__content").textContent = streamedContent;
      $("#messages").scrollTop = $("#messages").scrollHeight;
    });
    if (!result) throw new Error(t("requestFailed"));
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
    if (state.agentMode === mode) {
      renderConversation();
      if (!$('#message-input').value) $('#message-input').value = content;
    }
    toast(error.message, "error");
  } finally {
    state.sending = false;
    renderDatabaseChooser();
    renderInfraServerChooser();
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
    const [overview, users, settings, rag, infra, dataSchema, ldap, databaseConnection, profiles, infraProfiles] = await Promise.all([
      api("/admin/overview"),
      api("/admin/users"),
      api("/admin/settings"),
      api("/admin/rag/documents"),
      api("/admin/infra/status"),
      api("/admin/data/schema"),
      api("/admin/ldap"),
      api('/admin/data/connection'),
      api('/admin/data/connections'),
      api('/admin/infra/connections'),
    ]);
    $("#metric-users").textContent = overview.users_total;
    $("#metric-active").textContent = overview.users_active;
    $("#metric-chats").textContent = overview.conversations_total;
    $("#metric-messages").textContent = overview.messages_total;
    $("#users-status").textContent = t("accountsCount", { count: users.length });
    renderUsers(users);
    if (!state.settingsDirty) {
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
    }
    $("#sidebar-model").textContent = settings.model;
    $("#api-status").textContent = settings.api_configured ? "API ONLINE" : "API MISSING";
    $("#api-status").style.color = settings.api_configured ? "var(--mint)" : "var(--danger)";
    state.ragMaxDocuments = rag.capacity?.max_documents || 1000;
    renderDocuments(rag.documents);
    if (rag.capacity) $('#rag-capacity').textContent = t('ragCapacity', {
      count: rag.capacity.documents, max: rag.capacity.max_documents,
    });
    renderInfraStatus(infra);
    renderDataSchema(dataSchema.schema);
    if (!state.ldapDirty && !state.ldapBusy) renderLdapSettings(ldap);
    state.dbDefaultSettings = { ...databaseConnection, schema: dataSchema.schema, name: dataSchema.database };
    state.dbProfiles = profiles.connections;
    state.infraProfiles = infraProfiles.connections;
    if (!state.infraDirty && !state.infraBusy) {
      renderInfraProfiles();
      renderInfraProfile(state.infraProfiles.find((profile) => profile.id === state.infraProfileId));
    }
    if (!state.dbDirty && !state.dbBusy) {
      renderDatabaseProfiles();
      const selected = state.dbProfiles.find((p) => p.id === state.dbProfileId);
      if (state.dbProfileId !== 'new') renderDatabaseSettings(selected || databaseConnection);
    }
    $('#db-active-source').textContent = `${dataSchema.database} / READ-ONLY`;
    const selectedProfile = state.dbProfiles.find((p) => p.id === state.dbProfileId);
    if (selectedProfile) {
      renderDataSchema(selectedProfile.schema);
      $('#db-active-source').textContent = `${selectedProfile.name} / READ-ONLY`;
    }
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
    .filter((line) => /^[A-Za-z_][A-Za-z0-9_]*\(/.test(line));
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
  $('#rag-capacity').textContent = t('ragCapacity', { count: documents.length, max: state.ragMaxDocuments });
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
  state.ragUploading = true;
  drop.classList.add("uploading");
  status.textContent = t("uploading", { done: 0, total: files.length });

  try {
    const documents = [];
    for (const [index, file] of files.entries()) {
      documents.push({ name: file.name, content: await file.text() });
      status.textContent = t("uploading", { done: index + 1, total: files.length });
    }
    const created = await api("/admin/rag/documents/batch", {
      method: "POST",
      body: JSON.stringify({ documents }),
    });
    status.textContent = t("uploadDone", { count: created.documents.length });
    toast(t("filesAdded", { count: created.documents.length }));
    renderDocuments((await api("/admin/rag/documents")).documents);
  } catch (error) {
    status.textContent = error.message;
    toast(error.message, "error");
  } finally {
    state.ragUploading = false;
    $("#rag-file").value = "";
    drop.classList.remove("uploading", "dragging");
  }
}

function renderInfraServerChooser() {
  const control = $('#chat-infra-server');
  show($('#infra-server-switcher'), state.agentMode === 'infra');
  if (state.agentMode !== 'infra') return;
  const selected = state.activeConversation?.infra_connection_id || state.selectedInfraId || 'local';
  state.selectedInfraId = selected;
  control.replaceChildren();
  for (const server of state.infraChoices) control.add(new Option(server.name, server.id));
  if (!state.infraChoices.some((server) => server.id === selected)) {
    control.add(new Option(t('dbUnavailable'), selected));
  }
  control.value = selected;
  control.disabled = state.sending;
}

function selectChatInfraServer() {
  if (state.sending) { renderInfraServerChooser(); return; }
  const selected = $('#chat-infra-server').value;
  if (selected === state.selectedInfraId) return;
  if ($('#message-input').value.trim() && !window.confirm(t('discardChangesPrompt'))) {
    renderInfraServerChooser(); return;
  }
  $('#message-input').value = '';
  state.selectedInfraId = selected;
  state.activeConversationByAgent.infra = null;
  if (state.agentMode === 'infra') state.activeConversation = null;
  renderConversation();
  renderConversationList();
}

function renderInfraProfiles() {
  const control = $('#infra-profile');
  control.replaceChildren(new Option(t('infraNewServer'), 'new'));
  for (const profile of state.infraProfiles) control.add(new Option(profile.name, profile.id));
  if (state.infraProfileId !== 'new' && !state.infraProfiles.some((p) => p.id === state.infraProfileId)) state.infraProfileId = 'new';
  control.value = state.infraProfileId;
  show($('#infra-profile-delete'), state.infraProfileId !== 'new');
}

function renderInfraProfile(profile = {}) {
  $('#infra-kind').value = profile.kind || 'linux_ssh';
  $('#infra-profile-name').value = profile.name || '';
  $('#infra-host').value = profile.host || '';
  $('#infra-port').value = profile.port || ($('#infra-kind').value === 'windows_winrm' ? 5986 : 22);
  $('#infra-username').value = profile.username || '';
  $('#infra-identity').value = profile.identity_file || '';
  $('#infra-auth').value = profile.auth || 'ntlm';
  $('#infra-password').value = '';
  $('#infra-ca-file').value = profile.ca_file || '';
  $('#infra-password-help').textContent = t(profile.password_configured ? 'infraPasswordKeep' : 'infraPasswordNew');
  state.infraRevision = profile.revision || 0;
  infraFieldsVisibility(false);
  show($('#infra-test-result'), false);
}

function infraFieldsVisibility(resetPort = true) {
  const winrm = $('#infra-kind').value === 'windows_winrm';
  $$('.infra-ssh-field').forEach((field) => show(field, !winrm));
  $$('.infra-winrm-field').forEach((field) => show(field, winrm));
  $('#infra-identity').required = !winrm;
  $('#infra-password').required = winrm && state.infraProfileId === 'new';
  if (resetPort) $('#infra-port').value = winrm ? 5986 : 22;
}

function chooseInfraProfile(id) {
  if (state.infraBusy) return;
  if (state.infraDirty && !window.confirm(t('discardChangesPrompt'))) { renderInfraProfiles(); return; }
  state.infraProfileId = id;
  state.infraDirty = id === 'new';
  renderInfraProfiles();
  renderInfraProfile(state.infraProfiles.find((profile) => profile.id === id));
}

function infraPayload() {
  return { kind: $('#infra-kind').value, name: $('#infra-profile-name').value.trim(), host: $('#infra-host').value.trim(),
    port: Number($('#infra-port').value), username: $('#infra-username').value.trim(),
    identity_file: $('#infra-identity').value.trim(), password: $('#infra-password').value,
    auth: $('#infra-auth').value, ca_file: $('#infra-ca-file').value.trim(),
    revision: state.infraRevision };
}

async function infraConnectionAction(save) {
  if (state.infraBusy || !$('#infra-connection-form').reportValidity()) return;
  const profileId = state.infraProfileId;
  const base = `/admin/infra/connections${profileId === 'new' ? '' : '/' + profileId}`;
  state.infraBusy = true;
  $('#infra-form-fields').disabled = true;
  $('#infra-test').disabled = $('#infra-save').disabled = true;
  const output = $('#infra-test-result');
  output.textContent = t('dbTesting'); show(output);
  try {
    const result = await api(save ? base : `${base}/test`, {
      method: save && profileId !== 'new' ? 'PUT' : 'POST', body: JSON.stringify(infraPayload()),
    });
    if (save) {
      state.infraProfileId = result.id;
      state.infraDirty = false;
      output.textContent = t('infraSaveServer');
      await loadCapabilities();
    } else output.textContent = `${result.hostname} · ${formatDateTime(result.generated_at)}`;
  } catch (error) { output.textContent = error.message; output.classList.add('error'); }
  finally {
    state.infraBusy = false;
    $('#infra-form-fields').disabled = false;
    $('#infra-test').disabled = $('#infra-save').disabled = false;
    if (save && !state.infraDirty) await loadAdmin();
  }
}

async function deleteInfraProfile() {
  if (state.infraBusy || state.infraProfileId === 'new' || !window.confirm(t('infraDeleteServer') + '?')) return;
  try {
    await api(`/admin/infra/connections/${state.infraProfileId}?revision=${state.infraRevision}`, { method: 'DELETE' });
    state.infraProfileId = 'new'; state.infraDirty = false;
    await loadCapabilities(); await loadAdmin();
  } catch (error) { toast(error.message, 'error'); }
}

function renderDatabaseChooser() {
  const control = $('#chat-db-source');
  show($('#data-source-switcher'), state.agentMode === 'data');
  if (state.agentMode !== 'data') return;
  const selected = state.activeConversation?.database_connection_id || state.selectedDatabaseId || 'demo';
  state.selectedDatabaseId = selected;
  control.replaceChildren();
  for (const connection of state.databaseChoices) {
    control.add(new Option(connection.name, connection.id));
  }
  if (!state.databaseChoices.some((c) => c.id === selected)) {
    control.add(new Option(t('dbUnavailable'), selected));
  }
  control.value = selected;
  control.disabled = state.sending;
}

function selectChatDatabase() {
  if (state.sending) { renderDatabaseChooser(); return; }
  const selected = $('#chat-db-source').value;
  if (selected === state.selectedDatabaseId) return;
  if ($('#message-input').value.trim() && !window.confirm(t('discardChangesPrompt'))) {
    renderDatabaseChooser(); return;
  }
  $('#message-input').value = '';
  state.selectedDatabaseId = selected;
  state.activeConversationByAgent.data = null;
  if (state.agentMode === 'data') state.activeConversation = null;
  renderConversation();
  renderConversationList();
}

function renderDatabaseProfiles() {
  const control = $('#db-profile');
  control.replaceChildren(new Option(t('dbDefaultConnection'), 'default'));
  for (const profile of state.dbProfiles) control.add(new Option(profile.name, profile.id));
  if (state.dbProfileId === 'new') control.add(new Option(t('dbNewConnection'), 'new'));
  if (!['default', 'new'].includes(state.dbProfileId) && !state.dbProfiles.some((p) => p.id === state.dbProfileId)) state.dbProfileId = 'default';
  control.value = state.dbProfileId;
}

function chooseDatabaseProfile(id) {
  if (state.dbBusy) return;
  if (state.dbDirty && !window.confirm(t('discardChangesPrompt'))) { renderDatabaseProfiles(); return; }
  state.dbProfileId = id;
  state.dbDirty = id === 'new';
  renderDatabaseProfiles();
  const profile = id === 'new' ? {
    kind: 'postgresql', host: '', port: 5432, database: '', username: '', schema_name: 'public',
    tables: [], tls: true, revision: 0, read_only_confirmed: false, egress_confirmed: false, name: '',
  } : state.dbProfiles.find((p) => p.id === id) || state.dbDefaultSettings;
  if (profile) renderDatabaseSettings(profile);
  if (profile?.schema) {
    renderDataSchema(profile.schema);
    $('#db-active-source').textContent = `${profile.name} / READ-ONLY`;
  } else {
    renderDataSchema('');
    $('#db-active-source').textContent = t('dbNewConnection');
  }
  show($('#db-test-result'), false);
}

async function deleteDatabaseProfile() {
  if (state.dbBusy || ['default', 'new'].includes(state.dbProfileId)) return;
  if (!window.confirm(t('dbDeleteConfirm'))) return;
  state.dbBusy = true;
  $('#db-form-fields').disabled = true;
  $('#db-test').disabled = $('#db-save').disabled = true;
  try {
    await api(`/admin/data/connections/${state.dbProfileId}?revision=${state.dbRevision}`, { method: 'DELETE' });
    state.dbProfileId = 'default';
    state.dbDirty = false;
    await loadCapabilities();
  } catch (error) { toast(error.message, 'error'); }
  finally {
    state.dbBusy = false;
    $('#db-form-fields').disabled = false;
    $('#db-test').disabled = $('#db-save').disabled = false;
    await loadAdmin();
  }
}

function databaseFieldsVisibility() {
  const kind = $('#db-kind').value;
  const external = kind !== 'demo';
  const named = state.dbProfileId !== 'default';
  show($('#db-profile-name-row'), named);
  $('#db-profile-name').required = named;
  $('#db-profile-name').disabled = !named;
  show($('#db-profile-delete'), named && state.dbProfileId !== 'new');
  $('#db-kind option[value="demo"]').disabled = named;
  $('#db-save').textContent = t(named ? 'dbSaveConnection' : 'dbSave');
  show($('#db-external-fields'), external);
  $('#db-external-fields').disabled = !external;
  $$('[data-db-network]').forEach((element) => {
    show(element, kind !== 'sqlite');
    element.querySelectorAll('input').forEach((input) => { input.disabled = kind === 'sqlite'; });
  });
  $('#db-host').required = external && kind !== 'sqlite';
  $('#db-username').required = external && kind !== 'sqlite';
  $('#db-driver-note').textContent = t(kind === 'sqlite' ? 'dbSqliteNote' : kind === 'mssql' ? 'dbMssqlNote' : 'dbNetworkNote');
}

function renderDatabaseSettings(settings) {
  $('#db-profile-name').value = settings.name || '';
  state.dbRevision = settings.revision;
  $('#db-kind').value = settings.kind;
  $('#db-host').value = settings.host;
  $('#db-port').value = settings.port;
  $('#db-database').value = settings.database;
  $('#db-schema').value = settings.schema_name;
  $('#db-username').value = settings.username;
  $('#db-password').value = '';
  $('#db-tables').value = settings.tables.join(', ');
  $('#db-tls').checked = settings.tls;
  $('#db-read-only').checked = settings.read_only_confirmed;
  $('#db-egress').checked = settings.egress_confirmed;
  databaseFieldsVisibility();
}

function databasePayload() {
  return {
    kind: $('#db-kind').value, host: $('#db-host').value.trim(), port: Number($('#db-port').value) || 5432,
    database: $('#db-database').value.trim(), schema_name: $('#db-schema').value.trim(),
    username: $('#db-username').value.trim(), password: $('#db-password').value,
    tables: [...new Set($('#db-tables').value.split(',').map((name) => name.trim()).filter(Boolean))],
    tls: $('#db-tls').checked, read_only_confirmed: $('#db-read-only').checked,
    egress_confirmed: $('#db-egress').checked, revision: state.dbRevision,
  };
}

async function databaseAction(save) {
  if (state.dbBusy || !$('#db-connection-form').reportValidity()) return;
  const payload = databasePayload();
  const profileId = state.dbProfileId;
  const named = profileId !== 'default';
  if (named) payload.name = $('#db-profile-name').value.trim();
  const base = named ? `/admin/data/connections${profileId === 'new' ? '' : '/' + profileId}` : '/admin/data/connection';
  state.dbBusy = true;
  $('#db-form-fields').disabled = true;
  $('#db-test').disabled = true;
  $('#db-save').disabled = true;
  const output = $('#db-test-result');
  output.textContent = t('dbTesting');
  output.classList.remove('error');
  show(output);
  try {
    const result = await api(save ? base : `${base}/test`, {
      method: save && profileId !== 'new' ? 'PUT' : 'POST', body: JSON.stringify(payload),
    });
    if (save) {
      state.dbDirty = false;
      if (named) state.dbProfileId = result.id;
      renderDatabaseSettings(result);
      output.textContent = t(named ? 'dbProfileSaved' : 'dbSaved');
      await loadCapabilities();
      await loadAdmin();
    } else {
      output.textContent = `${t('dbTablesFound')}\n${result.tables.join(', ') || '—'}${result.tables_truncated ? '\n…' : ''}`;
    }
  } catch (error) {
    output.textContent = error.message;
    output.classList.add('error');
  } finally {
    state.dbBusy = false;
    $('#db-form-fields').disabled = false;
    $('#db-test').disabled = false;
    $('#db-save').disabled = false;
    databaseFieldsVisibility();
    if (save && !state.dbDirty) await loadAdmin();
  }
}

function renderLdapSettings(settings) {
  $("#ldap-enabled").checked = settings.enabled;
  $("#ldap-url").value = settings.url;
  $("#ldap-start-tls").checked = settings.start_tls;
  $("#ldap-verify-tls").checked = settings.verify_tls;
  $("#ldap-base-dn").value = settings.base_dn;
  $("#ldap-bind-dn").value = settings.bind_dn;
  $("#ldap-bind-password").value = "";
  $("#ldap-bind-password").placeholder = settings.bind_password_configured
    ? t("bindPasswordPlaceholder")
    : t("bindPassword");
  $("#ldap-user-filter").value = settings.user_filter;
  $("#ldap-name-attribute").value = settings.name_attribute;
  $("#ldap-email-attribute").value = settings.email_attribute;
  $("#ldap-auto-provision").checked = settings.auto_provision;
  $("#ldap-clear-password").checked = false;
  const status = $("#ldap-status");
  status.classList.toggle("online", settings.enabled);
  status.querySelector("strong").textContent = t(
    settings.enabled ? "ldapReady" : "ldapDisabled",
  );
}

function ldapSettingsPayload() {
  return {
    enabled: $("#ldap-enabled").checked,
    url: $("#ldap-url").value.trim(),
    start_tls: $("#ldap-start-tls").checked,
    verify_tls: $("#ldap-verify-tls").checked,
    base_dn: $("#ldap-base-dn").value.trim(),
    bind_dn: $("#ldap-bind-dn").value.trim(),
    bind_password: $("#ldap-bind-password").value,
    clear_bind_password: $("#ldap-clear-password").checked,
    user_filter: $("#ldap-user-filter").value.trim(),
    name_attribute: $("#ldap-name-attribute").value.trim(),
    email_attribute: $("#ldap-email-attribute").value.trim(),
    auto_provision: $("#ldap-auto-provision").checked,
  };
}

async function saveLdapSettings(form, quiet = false) {
  if (state.ldapBusy || !form.reportValidity()) return false;
  state.ldapBusy = true;
  const submitted = JSON.stringify(ldapSettingsPayload());
  const buttons = form.querySelectorAll("button");
  buttons.forEach((button) => { button.disabled = true; });
  try {
    const settings = await api("/admin/ldap", {
      method: "PUT",
      body: submitted,
    });
    if (JSON.stringify(ldapSettingsPayload()) === submitted) {
      state.ldapDirty = false;
      renderLdapSettings(settings);
    }
    if (!quiet) toast(t("ldapSaved"));
    return true;
  } catch (error) {
    toast(error.message, "error");
    return false;
  } finally {
    state.ldapBusy = false;
    buttons.forEach((button) => { button.disabled = false; });
  }
}

async function testLdapConnection() {
  if (state.ldapBusy || !$('#ldap-settings-form').reportValidity()) return;
  state.ldapBusy = true;
  const button = $("#ldap-test");
  const original = button.textContent;
  button.disabled = true;
  button.textContent = t("ldapTesting");
  try {
    await api("/admin/ldap/test", { method: "POST", body: JSON.stringify(ldapSettingsPayload()) });
    toast(t("ldapConnected"));
  } catch (error) {
    toast(error.message, "error");
  } finally {
    state.ldapBusy = false;
    button.disabled = false;
    button.textContent = original;
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
    role.disabled = user.id === state.user.id || user.auth_source === 'ldap';
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

function setSettingsDirty(dirty) {
  state.settingsDirty = Boolean(dirty);
  show($("#settings-dirty-bar"), state.settingsDirty);
}

async function saveSettings(form) {
  if (state.settingsSaving) return;
  state.settingsSaving = true;
  const buttons = [...new Set([
    form.querySelector('button[type="submit"]'),
    $("#settings-dirty-save"),
  ].filter(Boolean))];
  buttons.forEach((button) => {
    button.dataset.originalLabel = button.textContent;
    button.textContent = t("saving");
    button.disabled = true;
  });
  try {
    const savedSettings = await api("/admin/settings", {
      method: "PUT",
      body: JSON.stringify(settingsPayload()),
    });
    $("#sidebar-model").textContent = savedSettings.model;
    setSettingsDirty(false);
    await loadCapabilities();
    toast(t("settingsSaved"));
  } catch (error) {
    toast(error.message, "error");
  } finally {
    state.settingsSaving = false;
    buttons.forEach((button) => {
      button.textContent = button.dataset.originalLabel;
      button.disabled = false;
    });
  }
}

async function discardSettings() {
  if (!state.settingsDirty) return;
  if (!window.confirm(t("discardChangesPrompt"))) return;
  setSettingsDirty(false);
  await loadAdmin();
}

async function logout(notify = true) {
  if (notify && (state.settingsDirty || state.ldapDirty || state.dbDirty || state.infraDirty) && !window.confirm(t("discardChangesPrompt"))) return;
  state.dbDirty = false;
  state.dbProfileId = 'default';
  state.databaseChoices = [];
  state.selectedDatabaseId = null;
  state.infraProfiles = [];
  state.infraProfileId = 'new';
  state.infraDirty = false;
  state.infraChoices = [];
  state.selectedInfraId = null;
  $('#db-password').value = '';
  state.ldapDirty = false;
  $('#ldap-bind-password').value = '';
  try {
    await api("/auth/logout", { method: "POST" });
  } catch {}
  state.user = null;
  setSettingsDirty(false);
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
  $("#ldap-settings-form").addEventListener("submit", (event) => {
    event.preventDefault();
    saveLdapSettings(event.currentTarget);
  });
  $("#ldap-test").addEventListener("click", testLdapConnection);
  $('#db-connection-form').addEventListener('submit', (event) => { event.preventDefault(); databaseAction(true); });
  $('#db-test').addEventListener('click', () => databaseAction(false));
  $('#chat-db-source').addEventListener('change', selectChatDatabase);
  $('#chat-infra-server').addEventListener('change', selectChatInfraServer);
  $('#infra-connection-form').addEventListener('submit', (event) => { event.preventDefault(); infraConnectionAction(true); });
  $('#infra-test').addEventListener('click', () => infraConnectionAction(false));
  $('#infra-profile').addEventListener('change', () => chooseInfraProfile($('#infra-profile').value));
  $('#infra-profile-new').addEventListener('click', () => chooseInfraProfile('new'));
  $('#infra-profile-delete').addEventListener('click', deleteInfraProfile);
  $('#infra-kind').addEventListener('change', () => infraFieldsVisibility(true));
  $('#infra-connection-form').addEventListener('input', (event) => {
    if (event.target.id !== 'infra-profile') state.infraDirty = true;
  });
  $('#db-profile').addEventListener('change', () => chooseDatabaseProfile($('#db-profile').value));
  $('#db-profile-new').addEventListener('click', () => chooseDatabaseProfile('new'));
  $('#db-profile-delete').addEventListener('click', deleteDatabaseProfile);
  $('#db-connection-form').addEventListener('input', (event) => {
    if (event.target.id === 'db-profile') return;
    state.dbDirty = true;
    show($('#db-test-result'), false);
  });
  $('#db-kind').addEventListener('change', () => {
    const kind = $('#db-kind').value;
    $('#db-port').value = { postgresql: 5432, mysql: 3306, mariadb: 3306, mssql: 1433, oracle: 1521, sqlite: 5432, demo: 5432 }[kind];
    $('#db-schema').value = { postgresql: 'public', mssql: 'dbo', sqlite: 'main' }[kind] || '';
    $('#db-password').value = '';
    databaseFieldsVisibility();
  });
  $('#ldap-settings-form').addEventListener('input', () => { state.ldapDirty = true; });
  $('#ldap-enabled').addEventListener('input', () => { state.ldapDirty = true; });
  $("#settings-dirty-discard").addEventListener("click", discardSettings);
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
    "#settings-model",
    "#settings-prompt",
    "#rag-enabled",
    "#rag-max-chunks",
    "#infra-enabled",
    "#infra-admin-only",
    "#infra-live-enabled",
    "#infra-model",
    "#data-enabled",
    "#data-admin-only",
    "#data-model",
  ].forEach(
    (selector) => $(selector).addEventListener("input", () => setSettingsDirty(true)),
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
  window.addEventListener("beforeunload", (event) => {
    if (!state.settingsDirty && !state.ldapDirty && !state.dbDirty && !state.infraDirty) return;
    event.preventDefault();
    event.returnValue = "";
  });
  syncSidebarAccessibility();
}

initialize();
