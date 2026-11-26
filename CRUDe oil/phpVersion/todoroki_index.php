<?php
session_start();

// Redirect to login if user is not authenticated
if (!isset($_SESSION['user_id'])) {
    header("Location: todoroki_login.php");
    exit;
}

require_once 'todoroki_db.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

#CREATE
    if ($action === 'create') {
        $task = trim($_POST['task']);
        if (!empty($task)) {
            $stmt = $pdo->prepare("INSERT INTO tasks (task) VALUES (?)");
            $stmt->execute([$task]);

            // Log action
            $logStmt = $pdo->prepare("INSERT INTO task_logs (action_type, description) VALUES (?, ?)");
            $logStmt->execute(['CREATE', "Created task: '$task'"]);
        }
        header("Location: todoroki_index.php");
        exit;
    }

#UPDATE
    if ($action === 'update') {
        $id = $_POST['id'];
        $task = trim($_POST['task']);
        $status = $_POST['status'];
        if (!empty($task)) {
            $stmt = $pdo->prepare("UPDATE tasks SET task = ?, status = ? WHERE id = ?");
            $stmt->execute([$task, $status, $id]);

            // Log action
            $logStmt = $pdo->prepare("INSERT INTO task_logs (action_type, description) VALUES (?, ?)");
            $logStmt->execute(['UPDATE', "Updated task ID $id to '$task' (Status: $status)"]);
        }
        header("Location: todoroki_index.php");
        exit;
    }
}

#DELETE
if (isset($_GET['delete'])) {
    $id = $_GET['delete'];
    
    // Fetch task name for a better log description before deleting
    $getTask = $pdo->prepare("SELECT task FROM tasks WHERE id = ?");
    $getTask->execute([$id]);
    $taskData = $getTask->fetch(PDO::FETCH_ASSOC);
    $taskName = $taskData['task'] ?? "ID $id";

    $stmt = $pdo->prepare("DELETE FROM tasks WHERE id = ?");
    $stmt->execute([$id]);

    // Log action
    $logStmt = $pdo->prepare("INSERT INTO task_logs (action_type, description) VALUES (?, ?)");
    $logStmt->execute(['DELETE', "Deleted task: '$taskName'"]);

    header("Location: todoroki_index.php");
    exit;
}

#READ Tasks
$stmt = $pdo->query("SELECT * FROM tasks ORDER BY created_at DESC");
$tasks = $stmt->fetchAll(PDO::FETCH_ASSOC);

#READ Logs
$logStmt = $pdo->query("SELECT * FROM task_logs ORDER BY created_at DESC LIMIT 20");
$logs = $logStmt->fetchAll(PDO::FETCH_ASSOC);

$editTask = null;
if (isset($_GET['edit'])) {
    $stmt = $pdo->prepare("SELECT * FROM tasks WHERE id = ?");
    $stmt->execute([$_GET['edit']]);
    $editTask = $stmt->fetch(PDO::FETCH_ASSOC);
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prototype To-Do List</title>
    <!-- Bootstrap 5 CSS CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">

    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                
                <!-- Header with User Greeting and Logout -->
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2 class="mb-0">TO-DO-ROKI</h2>
                        <small class="text-muted">A prototype task list</small>
                    </div>
                    <div>
                        <span class="text-secondary me-2">Hello, <strong><?= htmlspecialchars($_SESSION['username']) ?></strong></span>
                        <a href="todoroki_logout.php" class="btn btn-outline-danger btn-sm">Logout</a>
                    </div>
                </div>
                
                <!-- Form: Add or Edit Task -->
                <div class="card shadow-sm mb-4">
                    <div class="card-body">
                        <form action="todoroki_index.php" method="POST">
                            <?php if ($editTask): ?>
                                <input type="hidden" name="action" value="update">
                                <input type="hidden" name="id" value="<?= $editTask['id'] ?>">
                                <h5 class="card-title mb-3">Edit Task</h5>
                            <?php else: ?>
                                <input type="hidden" name="action" value="create">
                                <h5 class="card-title mb-3">Add New Task</h5>
                            <?php endif; ?>

                            <div class="mb-3">
                                <input type="text" name="task" class="form-control" placeholder="What needs to be done?" value="<?= htmlspecialchars($editTask['task'] ?? '') ?>" required>
                            </div>

                            <?php if ($editTask): ?>
                                <div class="mb-3">
                                    <label class="form-label">Status</label>
                                    <select name="status" class="form-select">
                                        <option value="Pending" <?= $editTask['status'] === 'Pending' ? 'selected' : '' ?>>Pending</option>
                                        <option value="Completed" <?= $editTask['status'] === 'Completed' ? 'selected' : '' ?>>Completed</option>
                                    </select>
                                </div>
                                <button type="submit" class="btn btn-success">Update Task</button>
                                <a href="todoroki_index.php" class="btn btn-secondary">Cancel</a>
                            <?php else: ?>
                                <button type="submit" class="btn btn-primary">Add Task</button>
                            <?php endif; ?>
                        </form>
                    </div>
                </div>

                <!-- Display Task List -->
                <div class="card shadow-sm mb-4">
                    <div class="card-body">
                        <h5 class="card-title mb-3">Your Tasks</h5>
                        <?php if (count($tasks) > 0): ?>
                            <div class="list-group">
                                <?php foreach ($tasks as $t): ?>
                                    <div class="list-group-item d-flex justify-content-between align-items-center">
                                        <div>
                                            <span class="<?= $t['status'] === 'Completed' ? 'text-decoration-line-through text-muted' : '' ?>">
                                                <?= htmlspecialchars($t['task']) ?>
                                            </span>
                                            <br>
                                            <small class="badge bg-<?= $t['status'] === 'Completed' ? 'success' : 'warning' ?>">
                                                <?= $t['status'] ?>
                                            </small>
                                            <small class="text-muted ms-2"><?= $t['created_at'] ?></small>
                                        </div>
                                        <div>
                                            <a href="todoroki_index.php?edit=<?= $t['id'] ?>" class="btn btn-sm btn-outline-primary me-1">Edit</a>
                                            <a href="todoroki_index.php?delete=<?= $t['id'] ?>" class="btn btn-sm btn-outline-danger" onclick="return confirm('Are you sure you want to delete this task?');">Delete</a>
                                        </div>
                                    </div>
                                <?php endforeach; ?>
                            </div>
                        <?php else: ?>
                            <p class="text-muted mb-0">No tasks found. Enjoy your free time!</p>
                        <?php endif; ?>
                    </div>
                </div>

                <!-- Toggleable Activity Logs Section -->
                <div class="card shadow-sm">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">Activity Logs</h5>
                            <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#logsCollapse" aria-expanded="false" aria-controls="logsCollapse">
                                Toggle Logs
                            </button>
                        </div>
                        
                        <div class="collapse mt-3" id="logsCollapse">
                            <?php if (count($logs) > 0): ?>
                                <div class="list-group list-group-flush" style="max-height: 250px; overflow-y: auto;">
                                    <?php foreach ($logs as $log): ?>
                                        <div class="list-group-item px-0 py-2">
                                            <?php 
                                                $badgeColor = 'secondary';
                                                if ($log['action_type'] === 'CREATE') $badgeColor = 'primary';
                                                elseif ($log['action_type'] === 'UPDATE') $badgeColor = 'info';
                                                elseif ($log['action_type'] === 'DELETE') $badgeColor = 'danger';
                                            ?>
                                            <span class="badge bg-<?= $badgeColor ?>"><?= $log['action_type'] ?></span>
                                            <small class="text-muted ms-1"><?= htmlspecialchars($log['description']) ?></small>
                                            <br>
                                            <small class="text-muted" style="font-size: 0.75rem;"><?= $log['created_at'] ?></small>
                                        </div>
                                    <?php endforeach; ?>
                                </div>
                            <?php else: ?>
                                <p class="text-muted mb-0 small mt-2">No activity logs recorded yet.</p>
                            <?php endif; ?>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <!-- Bootstrap 5 JS Bundle CDN -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
