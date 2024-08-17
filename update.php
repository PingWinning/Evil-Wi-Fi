<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Updating...</title>
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
            text-align: center;
            max-width: 100%;
            width: 100%;
            max-width: 400px;
            padding: 20px;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
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
        h2 {
            font-size: 24px;
            margin-bottom: 20px;
            color: #333;
        }
        p {
            font-size: 16px;
            color: #666;
        }
    </style>
</head>
<body>

<div class="container">
    <h2>Updating Firmware...</h2>
    <div class="progress-bar">
        <div class="progress-bar-fill" id="progress"></div>
    </div>
    <p>Please do not turn off your router during the update.</p>
</div>

<script>
    window.onload = function() {
        var progressBar = document.getElementById('progress');
        progressBar.style.width = '100%';
    };
</script>

</body>
</html>
