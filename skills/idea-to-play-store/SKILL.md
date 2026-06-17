---
name: idea-to-play-store
description: "End-to-end Flutter app builder: from idea to Google Play. Automates trend research, idea validation, PRD/tasks, brand identity, Flutter code generation (full auto for standard apps), Firebase Auth, backend API, testing, signing, AAB build, store metadata, policy compliance, and publish guide. Use when asked to build a full mobile app from scratch, turn an idea into a published app, or create a Flutter MVP with Google Play submission. Don't use for single-phase work or non-mobile projects."
license: MIT
effort: max
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
---

# Idea to Play Store

5-phase orchestrator that takes an idea and produces a published Flutter app on Google Play.

**Stack:** Flutter (Dart) + FastAPI (Python, optional) + Firebase Auth + PostgreSQL.

## When to Use

Trigger when the user asks to:
- Build a Flutter app from an idea or trend
- "Turn idea into published app"
- Create a Flutter MVP with backend + Google Play submission
- "App từ ý tưởng đến CH Play"

Do **not** use for:
- Single-phase work (invoke the sibling skill directly)
- Web apps (use `idea-to-product`)
- Existing projects that only need one phase

## Prerequisites

### Required Skills

| Skill | Version | Phase | Source |
|-------|---------|-------|--------|
| `trend-ideas` | 1.0+ | 1 | global |
| `idea-validator` | 1.0+ | 1 | global |
| `brand-name-checker` | 1.0+ | 1 | skills repo |
| `prd-generator` | 1.0+ | 2 | global |
| `tad-generator` | 1.0+ | 2 | global |
| `tasks-generator` | 1.0+ | 2 | global |
| `logo-designer` | 1.0+ | 2 | global |
| `frontend-design` | 1.0+ | 2 | global |
| `flutter-init` | 1.0+ | 3 | skills repo |
| `firebase-auth-setup` | 1.0+ | 3 (opt) | global |
| `devops-pipeline` | 1.0+ | 3 | global |
| `code-review` | 1.0+ | 4 | global |
| `test-coverage` | 1.0+ | 4 | global |
| `flutter-signing` | 1.0+ | 5 | skills repo |
| `flutter-build` | 1.0+ | 5 | skills repo |
| `flutter-store-metadata` | 1.0+ | 5 | skills repo |
| `flutter-store-compliance` | 1.0+ | 5 | skills repo |
| `flutter-publish` | 1.0+ | 5 | skills repo |
| `release-manager` | 1.0+ | 5 | global |
| `aso-marketing` | 1.0+ | 5 | global |
| `social-poster` | 1.0+ | 5 (opt) | global |
| `deploy-render` | 1.0+ | 3 (opt) | global |

### Runtime Requirements

- **Flutter SDK 3.x+** (auto-installed by `flutter-init`)
- **Python 3.10+** (if backend needed)
- **Node.js 18+** (for Firebase tools)
- **Git** configured
- **Android Studio / Android SDK** (auto-configured by `flutter-init`)
- **macOS** (if iOS build needed; Linux for Android-only)

## Setup: Product Directory

### Step 0.1: Resolve Working Directory

1. Check if `$PRODUCT_DIR` is set → use it
2. Check `~/.config/idea-to-play-store-dir.txt` → read saved path
3. Ask user once, save to config file
4. Default: `~/workspace/products`

### Step 0.2: Create Project Folder

```bash
DATE=$(date +%Y_%m_%d)
mkdir -p "$PRODUCT_DIR/$DATE_$SLUG"
export PRODUCT_DIR="$PRODUCT_DIR/$DATE_$SLUG"
```

### Step 0.3: Create Sub-directories

```
$PRODUCT_DIR/
├── app/               # Flutter project (always)
├── backend/           # FastAPI (if needs_backend)
├── plan/              # PRD, TAD, Tasks
├── assets/            # Logo, UI mockups
└── store-metadata/    # Store listing assets
```

### Step 0.4: Init Git

```bash
cd "$PRODUCT_DIR"
git init
```

## Workflow

```
Phase 1 — Idea & Plan      → trend-ideas → idea-validator
                             → brand-name-checker → prd-generator
                             → tad-generator → tasks-generator
                             GATE: user approves PRD + tasks

Phase 2 — Brand & Design   → logo-designer → frontend-design
                             GATE: user approves logo + UI

Phase 3 — Setup & Backend  → flutter-init → [firebase-auth-setup]
                             → [backend-gen → deploy-render]
                             → devops-pipeline

Phase 4 — Build            → [feature-gen (parallel)] → build-runner
                             → flutter analyze → code-review
                             → test-coverage
                             GATE: user approves running app

Phase 5 — Store & Publish  → flutter-signing → flutter-build
                             → flutter-store-metadata
                             → flutter-store-compliance
                             → flutter-publish
                             → [aso-marketing → social-poster]
                             → release-manager
```

---

## Phase 1: Idea & Plan (Gate ⛔)

### Step 1a: Generate Ideas

```bash
/skill trend-ideas --output "$PRODUCT_DIR/plan/trend-report.md"
```

Parse output for winning idea (name + description + score).

### Step 1b: Validate Idea

```bash
/skill idea-validator "$PRODUCT_DIR/plan/trend-report.md" \
  --output "$PRODUCT_DIR/plan/validate.md"
```

Extract: app name, description, features, target audience.

### Step 1c: Check Brand Name

```bash
/skill brand-name-checker --name "$APP_NAME" \
  --output "$PRODUCT_DIR/plan/brand-check.md"
```

If `Abandon` verdict → suggest alternatives, ask user.

### Step 1d: Generate PRD

```bash
/skill prd-generator "$PRODUCT_DIR/plan/validate.md" \
  --output "$PRODUCT_DIR/plan/prd.md"
```

### Step 1e: Generate Architecture (TAD)

```bash
/skill tad-generator "$PRODUCT_DIR/plan/prd.md" \
  --output "$PRODUCT_DIR/plan/tad.md"
```

### Step 1f: Generate Tasks

```bash
/skill tasks-generator "$PRODUCT_DIR/plan/prd.md" \
  --arch "$PRODUCT_DIR/plan/tad.md" \
  --output "$PRODUCT_DIR/plan/tasks.md"
```

### Phase 1 Gate

```
◆ Phase 1 — Idea & Plan (COMPLETE)
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
  Trend ideas:     √ $N ideas generated
  Validation:      √ $APP_NAME — $SCORE/100
  Brand check:     √ $RISK level
  PRD:             √ $N features documented
  Architecture:    √ $STACK selected
  Tasks:           √ $N tasks created

  ⛔ User: Do you approve this plan?
     Options: Approve / Revise / Abort
```

**Gate logic:**
- Approved → advance to Phase 2
- Revise → ask user what to change, regenerate affected docs
- Abort → delete `$PRODUCT_DIR`, exit

---

## Phase 2: Brand & Design (Gate ⛔)

### Step 2a: Generate Logo

Read app name from PRD. Call:

```bash
/skill logo-designer --name "$APP_NAME" \
  --output "$PRODUCT_DIR/assets/logo/"
```

Copy icon assets to `$PRODUCT_DIR/assets/logo/`.

### Step 2b: Design UI Mockups

```bash
/skill frontend-design \
  --prd "$PRODUCT_DIR/plan/prd.md" \
  --platform mobile \
  --output "$PRODUCT_DIR/assets/ui-mockups/"
```

This generates mobile UI mockups (HTML + CSS or Figma links).

### Phase 2 Gate

```
◆ Phase 2 — Brand & Design (COMPLETE)
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
  Logo:       √ 7 variants created
  UI Design:  √ $N screens mocked up

  ⛔ User: Do you approve the brand & design?
     Options: Approve / Revise
```

---

## Phase 3: Setup & Backend

### Step 3a: Initialize Flutter Project

Read app_name + org from PRD.

```bash
/skill flutter-init \
  --project_name "$SLUG" \
  --org "$ORG" \
  --platforms "android,ios" \
  --dir "$PRODUCT_DIR/app/"
```

This creates the Flutter project under `$PRODUCT_DIR/app/`.

### Step 3b: Firebase Auth Setup (Optional)

Check PRD for `auth` / `login` / `register` keywords:

```bash
grep -qi "auth\|login\|register\|sign.in\|đăng.nhập" "$PRODUCT_DIR/plan/prd.md"
```

If auth needed:

```bash
/skill firebase-auth-setup \
  --project "$SLUG" \
  --app-type flutter \
  --output "$PRODUCT_DIR/app/lib/core/network/"
```

This:
- Creates Firebase project
- Enables Email/Password + Google Auth
- Generates `google-services.json` into `android/app/`
- Generates `firebase_options.dart`

### Step 3c: Generate Backend (Optional)

Check PRD for backend needs:

```bash
grep -qi "api\|server\|sync\|cloud\|user.data" "$PRODUCT_DIR/plan/prd.md"
```

If backend needed, generate FastAPI project:

```
$PRODUCT_DIR/backend/
├── main.py                # FastAPI entry + CORS + Firebase verify
├── database.py            # SQLAlchemy + PostgreSQL (or SQLite local)
├── requirements.txt       # fastapi, uvicorn, firebase-admin, sqlalchemy, psycopg2
├── Dockerfile
├── render.yaml
├── app/
│   ├── __init__.py
│   ├── config.py          # Firebase creds, DB URL
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py        # User model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py         # POST /api/auth/verify — verify Firebase token
│   │   └── users.py        # GET/PUT /api/users/me
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── auth_service.py  # Firebase Admin verification
│   └── middleware/
│       ├── __init__.py
│       └── firebase_auth.py  # Dependency: get_current_user
└── .env.example
```

**Key backend code (main.py):**

```python
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

cred = credentials.Certificate("service-account.json")
firebase_admin.initialize_app(cred)

app = FastAPI(title="$APP_NAME API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

security = HTTPBearer(auto_error=False)

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        decoded = auth.verify_id_token(credentials.credentials)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/users/me")
async def get_me(user: dict = Depends(verify_token)):
    return {"uid": user["uid"], "email": user.get("email"), "name": user.get("name")}
```

After generating, if user wants to deploy:

```bash
/skill deploy-render \
  --server-dir "$PRODUCT_DIR/backend/" \
  --slug "$SLUG-backend" \
  --db postgres
```

### Step 3d: DevOps Pipeline

```bash
/skill devops-pipeline --dir "$PRODUCT_DIR/app/"
```

### Phase 3 Report

```
◆ Phase 3 — Setup & Backend (COMPLETE)
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
  Flutter project:   √ $SLUG created at app/
  Firebase Auth:     √ Email/Google enabled
  Backend API:       √ FastAPI at backend/ ($N routes)
  DevOps:            √ Pre-commit hooks + CI
```

No gate — proceed to Phase 4.

---

## Phase 4: Build (Gate ⛔)

This is the core code generation phase. It parses `tasks.md` and generates full Flutter code for each feature.

### Step 4a: Parse Tasks into Feature Definitions

Read `$PRODUCT_DIR/plan/tasks.md`. Extract each task and classify:

**Task classification rules:**

| Task contains... | Feature type |
|-----------------|--------------|
| "CRUD", "list", "manage", "quản lý" + noun | `crud` |
| "login", "register", "sign in", "đăng nhập" | `auth` |
| "search", "tìm kiếm", "filter" | `search` |
| "profile", "account", "tài khoản" | `profile` |
| "settings", "cài đặt", "preferences" | `settings` |
| "onboarding", "intro", "giới thiệu" | `onboarding` |
| "map", "location", "bản đồ" | `map` |
| "camera", "photo", "scan" | `camera` |
| "chart", "report", "thống kê" | `charts` |
| "webview", "browser", "web" | `webview` |
| "notification", "push", "thông báo" | `notifications` |

**Extract fields from task description:**

Use regex to find structured data:

```
Task: "User can create todos with title, description, due date, priority"
→ Feature: todos (type: crud)
→ Fields: title (string, required), description (string), due_date (date), priority (enum: low/medium/high)
```

```bash
# Extract feature name (first noun after "manage/crud/list")
FEATURE_NAME=$(echo "$TASK" | grep -oiP "(manage|list|crud)\s+\K\w+" || echo "untitled")
```

### Step 4b: Feature Code Generation (Parallel Subagents)

Spawn one subagent per feature (parallel):

```
/agent feature-gen-crud \
  --name "$FEATURE_NAME" \
  --fields "$FIELDS_JSON" \
  --auth "$NEEDS_AUTH" \
  --api "$HAS_API" \
  --dir "$PRODUCT_DIR/app/"
```

Each feature-gen subagent produces:

**For `crud` type (most common):**

`lib/features/todos/models/todo.dart`:
```dart
class Todo {
  final int? id;
  final String title;
  final String? description;
  final DateTime? dueDate;
  final String priority;
  final bool completed;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  Todo({
    this.id,
    required this.title,
    this.description,
    this.dueDate,
    this.priority = 'medium',
    this.completed = false,
    this.createdAt,
    this.updatedAt,
  });

  factory Todo.fromJson(Map<String, dynamic> json) => Todo(
    id: json['id'] as int?,
    title: json['title'] as String,
    description: json['description'] as String?,
    dueDate: json['due_date'] != null ? DateTime.parse(json['due_date']) : null,
    priority: json['priority'] as String? ?? 'medium',
    completed: json['completed'] as bool? ?? false,
    createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : null,
    updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : null,
  );

  Map<String, dynamic> toJson() => {
    if (id != null) 'id': id,
    'title': title,
    if (description != null) 'description': description,
    if (dueDate != null) 'due_date': dueDate!.toIso8601String(),
    'priority': priority,
    'completed': completed,
  };

  Todo copyWith({...});
}
```

`lib/features/todos/providers/todo_provider.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/todo.dart';
import '../services/todo_service.dart';

enum TodoFilter { all, active, completed }

final todoFilterProvider = StateProvider<TodoFilter>((ref) => TodoFilter.all);

final todoListProvider = StateNotifierProvider<TodoListNotifier, AsyncValue<List<Todo>>>((ref) {
  return TodoListNotifier(ref.read(todoServiceProvider));
});

class TodoListNotifier extends StateNotifier<AsyncValue<List<Todo>>> {
  final TodoService _service;

  TodoListNotifier(this._service) : super(const AsyncValue.loading()) {
    fetchAll();
  }

  Future<void> fetchAll() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => _service.fetchAll());
  }

  Future<void> create(Todo todo) async {
    await _service.create(todo);
    await fetchAll();
  }

  Future<void> update(int id, Todo todo) async {
    await _service.update(id, todo);
    await fetchAll();
  }

  Future<void> delete(int id) async {
    await _service.delete(id);
    await fetchAll();
  }
}
```

`lib/features/todos/services/todo_service.dart`:
```dart
// Local (no backend)
class TodoService {
  final List<Todo> _localStore = [];

  Future<List<Todo>> fetchAll() async => _localStore;
  Future<Todo> create(Todo todo) async { _localStore.add(todo); return todo; }
  Future<void> update(int id, Todo todo) async { /* find and replace */ }
  Future<void> delete(int id) async { _localStore.removeWhere((t) => t.id == id); }
}
```

Or with API:

```dart
// Remote (with backend)
class TodoService {
  final ApiClient _api;

  TodoService(this._api);

  Future<List<Todo>> fetchAll() async {
    final res = await _api.get('/api/todos');
    return (res.data as List).map((j) => Todo.fromJson(j)).toList();
  }

  Future<Todo> create(Todo todo) async {
    final res = await _api.post('/api/todos', data: todo.toJson());
    return Todo.fromJson(res.data);
  }

  Future<void> update(int id, Todo todo) async {
    await _api.put('/api/todos/$id', data: todo.toJson());
  }

  Future<void> delete(int id) async {
    await _api.delete('/api/todos/$id');
  }
}
```

`lib/features/todos/screens/todo_list_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/todo_provider.dart';
import '../widgets/todo_card.dart';
import 'todo_form_screen.dart';

class TodoListScreen extends ConsumerWidget {
  const TodoListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final todosAsync = ref.watch(todoListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Todos')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => Navigator.push(context, MaterialPageRoute(
          builder: (_) => const TodoFormScreen(),
        )),
        child: const Icon(Icons.add),
      ),
      body: todosAsync.when(
        data: (todos) => todos.isEmpty
          ? const Center(child: Text('No todos yet'))
          : ListView.builder(
              itemCount: todos.length,
              itemBuilder: (_, i) => TodoCard(todo: todos[i]),
            ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}
```

`lib/features/todos/screens/todo_form_screen.dart`:
```dart
// Auto-generated form with fields from FieldDefinition
// title → TextFormField with validation
// description → TextFormField (multiline)
// dueDate → DatePicker
// priority → DropdownButtonFormField
// Submit → calls provider.create() or provider.update()
```

`lib/features/todos/screens/todo_detail_screen.dart`:
```dart
// Shows all fields read-only
// Edit button → navigate to form with existing data
// Delete button → confirm dialog → provider.delete()
// Back button → pop
```

`lib/features/todos/widgets/todo_card.dart`:
```dart
// Card showing title, priority badge, due date
// Checkbox for completed status
// onTap → navigate to detail
```

**For `auth` type:**

`lib/features/auth/providers/auth_provider.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';

final authProvider = StateNotifierProvider<AuthNotifier, AsyncValue<User?>>((ref) {
  return AuthNotifier();
});

class AuthNotifier extends StateNotifier<AsyncValue<User?>> {
  final _auth = FirebaseAuth.instance;

  AuthNotifier() : super(const AsyncValue.data(null)) {
    _auth.authStateChanges().listen((user) {
      state = AsyncValue.data(user);
    });
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final cred = await _auth.signInWithEmailAndPassword(email: email, password: password);
      return cred.user;
    });
  }

  Future<void> register(String email, String password) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final cred = await _auth.createUserWithEmailAndPassword(email: email, password: password);
      return cred.user;
    });
  }

  Future<void> loginWithGoogle() async {
    // Google Sign-In implementation
  }

  Future<void> logout() async {
    await _auth.signOut();
    state = const AsyncValue.data(null);
  }
}
```

`lib/features/auth/screens/login_screen.dart`:
```dart
class LoginScreen extends ConsumerWidget {
  // Email field, password field
  // Login button → authProvider.login()
  // "Don't have account?" → navigate to register
  // Google Sign-In button
}
```

`lib/features/auth/screens/register_screen.dart`:
```dart
// Email, password, confirm password
// Register button → authProvider.register()
// Back to login link
```

**For `settings` type:**

`lib/features/settings/screens/settings_screen.dart`:
```dart
// Theme toggle (light/dark/system)
// Notifications on/off
// App version
// Logout button (if auth)
// Delete account
```

**For `profile` type:**

`lib/features/profile/screens/profile_screen.dart`:
```dart
// Avatar, name, email, phone
// Edit button → edit profile screen
```

### Step 4c: Generate App Shell (auto_route)

After all features complete, generate routing:

`lib/config/routes.dart`:
```dart
import 'package:go_router/go_router.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (_, __) => const HomeScreen()),
    GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
    GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
    GoRoute(path: '/todos', builder: (_, __) => const TodoListScreen()),
    GoRoute(path: '/todos/new', builder: (_, __) => const TodoFormScreen()),
    GoRoute(path: '/todos/:id', builder: (_, state) => TodoDetailScreen(id: state.pathParameters['id']!)),
    GoRoute(path: '/todos/:id/edit', builder: (_, state) => TodoFormScreen(id: state.pathParameters['id']!)),
    GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
    GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
  ],
);
```

### Step 4d: Generate Main App Shell

`lib/app.dart`:
```dart
import 'package:flutter/material.dart';
import 'config/routes.dart';
import 'config/theme.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: '$APP_NAME',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: appRouter,
      debugShowCheckedModeBanner: false,
    );
  }
}
```

`lib/main.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: MyApp()));
}
```

### Step 4e: Generate Core Infrastructure

`lib/core/network/api_client.dart` (if backend):
```dart
import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient({required String baseUrl}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final user = FirebaseAuth.instance.currentUser;
        if (user != null) {
          final token = await user.getIdToken();
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
    ));
  }

  Future<Response> get(String path, {Map<String, dynamic>? params}) => _dio.get(path, queryParameters: params);
  Future<Response> post(String path, {dynamic data}) => _dio.post(path, data: data);
  Future<Response> put(String path, {dynamic data}) => _dio.put(path, data: data);
  Future<Response> delete(String path) => _dio.delete(path);
}
```

### Step 4f: Configure Dependencies

Update `pubspec.yaml` with all needed packages:

```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.5.0
  go_router: ^14.0.0
  dio: ^5.4.0
  json_annotation: ^4.8.0
  intl: ^0.19.0
  shimmer: ^3.0.0
  flutter_secure_storage: ^9.0.0
  # Conditionally added:
  firebase_core: ^3.0.0
  firebase_auth: ^5.0.0
  google_sign_in: ^6.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.0
  json_serializable: ^6.7.0
  flutter_lints: ^4.0.0
```

### Step 4g: Run Build Runner

```bash
cd "$PRODUCT_DIR/app"
dart run build_runner build --delete-conflicting-outputs 2>&1
```

If errors → fix imports, retry.

### Step 4h: Verify with flutter analyze

```bash
cd "$PRODUCT_DIR/app"
flutter analyze 2>&1
```

**Auto-fix common errors:**
- Missing import → add
- Invalid constructor → fix syntax
- Undefined class → check naming
- Unused import → remove

### Step 4i: Code Review & Tests

```bash
/skill code-review "$PRODUCT_DIR/app/" \
  --output "$PRODUCT_DIR/plan/code-review.md"

/skill test-coverage "$PRODUCT_DIR/app/" \
  --framework flutter_test \
  --output "$PRODUCT_DIR/plan/test-coverage.md"
```

### Phase 4 Gate

```
◆ Phase 4 — Build (COMPLETE)
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
  Features generated: √ $N features
  Routes registered:  √ $N routes
  flutter analyze:    √ 0 errors, 0 warnings
  Code review:        √ $FINDINGS findings
  Test coverage:      √ $PERCENT%

  ┌─────────────────────────────────────────────┐
  │  $PRODUCT_DIR/app/                          │
  │                                             │
  │  lib/                                       │
  │  ├── main.dart                              │
  │  ├── app.dart                               │
  │  ├── config/ (theme + routes)               │
  │  ├── core/ (network, constants, widgets)    │
  │  └── features/                              │
  │      ├── auth/          (2 screens)         │
  │      ├── todos/         (3 screens)         │
  │      ├── profile/       (1 screen)          │
  │      └── settings/      (1 screen)          │
  └─────────────────────────────────────────────┘

  ⛔ User: Do you approve the built app?
     Options: Approve / Retry / Manual fix
```

**Gate logic:**
- Approved → continue to Phase 5
- Retry → fix reported issues and re-run analyze
- Manual fix → pause orchestrator, let user edit, resume

---

## Phase 5: Store & Publish

### Step 5a: Configure Signing

```bash
/skill flutter-signing \
  --dir "$PRODUCT_DIR/app/"
```

### Step 5b: Build Release AAB

```bash
/skill flutter-build \
  --dir "$PRODUCT_DIR/app/" \
  --type appbundle \
  --obfuscate true
```

AAB saved to `$PRODUCT_DIR/app/build/release/app-release.aab`.

### Step 5c: Generate Store Assets

```bash
/skill flutter-store-metadata \
  --app_name "$APP_NAME" \
  --features "$FEATURES" \
  --category "$CATEGORY" \
  --has_login $(grep -qi "auth\|login" "$PRODUCT_DIR/plan/prd.md" && echo true || echo false) \
  --collects_data $(grep -qi "auth\|profile\|data" "$PRODUCT_DIR/plan/prd.md" && echo true || echo false) \
  --has_ads $(grep -qi "ad\|ads\|quảng.cáo" "$PRODUCT_DIR/plan/prd.md" && echo true || echo false) \
  --output "$PRODUCT_DIR/store-metadata/"
```

### Step 5d: Compliance Check

```bash
/skill flutter-store-compliance \
  --features "$FEATURES" \
  --has_login $(...) \
  --collects_data $(...) \
  --has_ads $(...) \
  --has_inapp_purchase $(...) \
  --target_children $(grep -qi "children\|kid\|child\|trẻ.em" "$PRODUCT_DIR/plan/prd.md" && echo true || echo false) \
  --has_ugc $(grep -qi "user.content\|post\|comment\|bình.luận" "$PRODUCT_DIR/plan/prd.md" && echo true || echo false) \
  --uses_sensitive_permissions $(...) \
  --dir "$PRODUCT_DIR/app/" \
  --store-dir "$PRODUCT_DIR/store-metadata/"
```

If compliance `FAIL` → list issues, ask user to fix, re-run.

### Step 5e: Publish Guide

```bash
/skill flutter-publish \
  --aab_path "$(find $PRODUCT_DIR/app/build -name '*.aab' -type f | head -1)" \
  --app_name "$APP_NAME" \
  --category "$CATEGORY" \
  --track "$TRACK" \
  --whats_new "$PRODUCT_DIR/store-metadata/whats-new.txt" \
  --output "$PRODUCT_DIR/store-metadata/publish-guide.md"
```

### Step 5f: ASO Optimization (Optional)

```bash
/skill aso-marketing \
  --app-name "$APP_NAME" \
  --description "$(cat $PRODUCT_DIR/store-metadata/description/full_description.txt)" \
  --features "$FEATURES" \
  --output "$PRODUCT_DIR/store-metadata/aso-report.md"
```

### Step 5g: Release Management

```bash
cd "$PRODUCT_DIR"
git add -A
git commit -m "feat: $APP_NAME initial release"
git tag v1.0.0
/skill release-manager --version 1.0.0 --skip-questions
```

### Step 5h: Social Post (Optional)

```bash
/skill social-poster \
  --app-name "$APP_NAME" \
  --description "$SHORT_DESC" \
  --play-store-url "https://play.google.com/store/apps/details?id=$PACKAGE_NAME"
```

### Phase 5 Report

```
◆ Phase 5 — Store & Publish (COMPLETE)
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
  Signing:         √ Keystore created
  Build:           √ AAB generated ($(ls -lh store-metadata/*.aab))
  Store listing:   √ Icon, screenshots, description
  Compliance:      √ PASS ($PASS_COUNT/$TOTAL areas)
  Publish guide:   √ Step-by-step instructions
  ASO report:      √ Keywords optimized

  📦 $PRODUCT_DIR/store-metadata/ contains everything needed
  🔐 Compliance status: $COMPLIANCE
```

---

## Final Report

```
═══════════════════════════════════════════════════
  FINAL REPORT: $APP_NAME
═══════════════════════════════════════════════════

  Phase 1  Idea & Plan        √ pass  (idea validated $SCORE/100)
  Phase 2  Brand & Design     √ pass  (logo + UI approved)
  Phase 3  Setup & Backend    √ pass  (Flutter + backend ready)
  Phase 4  Build              √ pass  ($N features, $N screens, 0 errors)
  Phase 5  Store & Publish    √ pass  (ready to submit)

  Project path:   $PRODUCT_DIR/
  App source:     $PRODUCT_DIR/app/
  Backend API:    $PRODUCT_DIR/backend/ $(if deployed: → $RENDER_URL)
  Store assets:   $PRODUCT_DIR/store-metadata/
  Plans:          $PRODUCT_DIR/plan/

  Package name:   $ORG.$SLUG
  Version:        1.0.0

  Next steps:
  1. Open Play Console: https://play.google.com/console/
  2. Create new app
  3. Upload AAB from $AAB_PATH
  4. Fill store listing from $PRODUCT_DIR/store-metadata/
  5. Submit for review

  ⏱ Google Play review time: 1-7 days
```

---

## Feature Template Reference

### Feature: `crud`
Files generated: 6
```
features/<name>/
├── models/<name>.dart          # Data class + fromJson/toJson/copyWith
├── providers/<name>_provider.dart  # StateNotifier with CRUD operations
├── screens/<name>_list_screen.dart  # List + FAB + pull-to-refresh
├── screens/<name>_detail_screen.dart  # Read-only detail view
├── screens/<name>_form_screen.dart    # Create/edit form with validation
├── widgets/<name>_card.dart           # List item card widget
└── services/<name>_service.dart       # API calls or local storage
```

### Feature: `auth`
Files generated: 4
```
features/auth/
├── models/user.dart
├── providers/auth_provider.dart
├── screens/login_screen.dart
└── screens/register_screen.dart
```

### Feature: `settings`
Files generated: 1
```
features/settings/
└── screens/settings_screen.dart
```

### Feature: `profile`
Files generated: 2
```
features/profile/
├── providers/profile_provider.dart
└── screens/profile_screen.dart
```

### Feature: `search`
Files generated: 1
```
features/search/
└── screens/search_screen.dart
```

---

## Edge Cases

| Situation | Handling |
|-----------|----------|
| No trend ideas found | Fallback: ask user for direct idea input |
| Brand name returns Abandon | Suggest 3 alternatives, re-check |
| User disapproves at Phase 1 gate | Ask what to change, revise specific doc |
| Flutter install fails | Print error, try manual install path |
| Firebase project creation fails | Guide to create manually in Firebase Console |
| Backend deploy fails | Suggest Render manual deploy, continue without backend |
| `flutter analyze` has errors | Auto-fix (add imports, fix syntax), retry up to 3 times |
| Build runner conflicts | `clean` then rebuild |
| Compliance FAIL | Print specific items, block Phase 5, ask user to fix |
| User cancels mid-pipeline | Save state to `$PRODUCT_DIR/.idea-play-store-state` for resume |

## Acceptance Criteria

- [ ] All 5 phases complete without critical errors
- [ ] Flutter app compiles with `flutter analyze` clean
- [ ] Feature code generated for every task in tasks.md
- [ ] Backend API generated if PRD requires backend
- [ ] Firebase Auth integrated if PRD requires login
- [ ] Store metadata generated (icon, screenshots, desc, privacy policy)
- [ ] Compliance check PASS or PARTIAL
- [ ] Publish guide generated with step-by-step instructions
- [ ] Final report produced with all deliverables listed
