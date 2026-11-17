<?php
session_start();
session_unset();
session_destroy();
header("Location: todoroki_login.php");
exit;