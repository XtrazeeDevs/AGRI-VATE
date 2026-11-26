<?php
session_start();
require_once 'todoroki_db.php';

$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? 'login';
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if (empty($username) || empty($password)) {
        $error = "Please fill in all fields.";
    } else {
        if ($action === 'register') {
            // Check if user already exists
            $stmt = $pdo->prepare("SELECT id FROM users WHERE username = ?");
            $stmt->execute([$username]);
            if ($stmt->fetch()) {
                $error = "Username already taken. Please choose another.";
            } else {
                // Insert new user with hashed password
                $hashedPassword = password_hash($password, PASSWORD_DEFAULT);
                $stmt = $pdo->prepare("INSERT INTO users (username, password) VALUES (?, ?)");
                if ($stmt->execute([$username, $hashedPassword])) {
                    $success = "Registration successful! You can now log in.";
                } else {
                    $error = "Registration failed. Please try again.";
                }
            }
        } elseif ($action === 'login') {
            // Authenticate user
            $stmt = $pdo->prepare("SELECT * FROM users WHERE username = ?");
            $stmt->execute([$username]);
            $user = $stmt->fetch(PDO::FETCH_ASSOC);

            if ($user && password_verify($password, $user['password'])) {
                // Set session variables
                $_SESSION['user_id'] = $user['id'];
                $_SESSION['username'] = $user['username'];
                header("Location: todoroki_index.php");
                exit;
            } else {
                $error = "Invalid username or password.";
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - TO-DO-ROKI</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex align-items-center py-5" style="min-height: 100vh;">

    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-5">
                <h2 class="text-center mb-4">TO-DO-ROKI</h2>
                <div class="card shadow-sm">
                    <div class="card-body p-4">
                        <h4 class="card-title mb-3 text-center">Welcome Back</h4>

                        <?php if (!empty($error)): ?>
                            <div class="alert alert-danger py-2"><?= htmlspecialchars($error) ?></div>
                        <?php endif; ?>

                        <?php if (!empty($success)): ?>
                            <div class="alert alert-success py-2"><?= htmlspecialchars($success) ?></div>
                        <?php endif; ?>

                        <form action="todoroki_login.php" method="POST">
                            <input type="hidden" name="action" id="formAction" value="login">
                            
                            <div class="mb-3">
                                <label class="form-label">Username</label>
                                <input type="text" name="username" class="form-control" required>
                            </div>

                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>

                            <div class="d-grid gap-2">
                                <button type="submit" id="submitBtn" class="btn btn-primary">Login</button>
                            </div>
                        </form>

                        <div class="mt-3 text-center">
                            <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" id="toggleAuthMode">
                                Don't have an account? Register here
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const toggleBtn = document.getElementById('toggleAuthMode');
        const formAction = document.getElementById('formAction');
        const submitBtn = document.getElementById('submitBtn');
        const cardTitle = document.querySelector('.card-title');

        let isRegister = false;

        toggleBtn.addEventListener('click', () => {
            isRegister = !isRegister;
            if (isRegister) {
                formAction.value = 'register';
                submitBtn.textContent = 'Register';
                submitBtn.classList.replace('btn-primary', 'btn-success');
                cardTitle.textContent = 'Create Account';
                toggleBtn.textContent = 'Already have an account? Login here';
            } else {
                formAction.value = 'login';
                submitBtn.textContent = 'Login';
                submitBtn.classList.replace('btn-success', 'btn-primary');
                cardTitle.textContent = 'Welcome Back';
                toggleBtn.textContent = "Don't have an account? Register here";
            }
        });
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
