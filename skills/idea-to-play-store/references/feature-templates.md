# Flutter feature templates

Used by Phase 4b. One template per feature type; substitute the feature name and fields extracted from `tasks.md`. Stack: Riverpod (`flutter_riverpod`), `go_router`, `dio` (only when a backend exists), `firebase_auth` (only when `needs_auth`).

Everything below is a **shape**, not text to paste. Field types, nullability and validation come from the task definition; `// ...` comments mark where the generator writes real code, and a file must not ship with those comments still in it.

## Feature code by type

### `crud` (most common)

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

### `auth`

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

  // Only generate when firebase-output.json → auth_providers contains "google".
  // Needs google_sign_in + the OAuth client firebase-auth-setup could not create for you.
  Future<void> loginWithGoogle() async { /* GoogleSignIn().signIn() → credential → _auth.signInWithCredential */ }

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

### `settings`

`lib/features/settings/screens/settings_screen.dart`:
```dart
// Theme toggle (light/dark/system)
// Notifications on/off
// App version
// Logout button (if auth)
// Delete account
```

### `profile`

`lib/features/profile/screens/profile_screen.dart`:
```dart
// Avatar, name, email, phone
// Edit button → edit profile screen
```

## App shell — routing (go_router)

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

## App shell — `app.dart` / `main.dart`

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

## Core infrastructure

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

## pubspec dependencies

Add what the generated features import — nothing more. Versions below are floors known to resolve together at the time of writing; run `flutter pub outdated` rather than trusting them. `dio` only with a backend; `json_annotation`/`json_serializable`/`build_runner` only if a model actually uses `@JsonSerializable` (the hand-written `fromJson` above does not).

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
  # Only when needs_auth:
  firebase_core: ^3.0.0
  firebase_auth: ^5.0.0
  # Only when auth_providers contains "google":
  google_sign_in: ^6.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.0
  json_serializable: ^6.7.0
  flutter_lints: ^4.0.0
```

## File inventory per feature type

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
