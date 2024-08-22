![image](https://github.com/user-attachments/assets/86283f1a-3584-44b8-857f-670f2cc0d126)

# Evil-Wi-Fi Phishing Simulation

## Overview

The **Evil-Wi-Fi Phishing Simulation** is a white hat penetration testing tool designed to evaluate and enhance user awareness of phishing attacks targeting Wi-Fi credentials. This project creates a controlled environment where users are presented with a fake router firmware update page, prompting them to enter their Wi-Fi password.

## Features

- **Phishing Simulation**: Mimics a router gateway interface that displays a message requiring the user to enter their Wi-Fi password for a firmware update.
- **Data Logging**: Captures and logs submitted passwords, along with metadata such as the user's IP address, in a hidden `.logs` file for analysis.
- **Update Simulation**: After submission, the user is redirected to a page with a 5-minute loading bar that simulates a firmware update process.
- **Responsive Design**: The interface is optimized for both small and large screens, ensuring a convincing experience across devices.

![image](https://github.com/user-attachments/assets/002123af-efee-4b5d-bcec-012f81ab4715)

## Project Structure

![image](https://github.com/user-attachments/assets/24a7edfa-29db-40d3-b5a0-a5dba311b9af)

## Usage

1. **Deploy the Project**: Upload the contents of the `evil-Wi-Fi` directory to your testing environment, such as a Wi-Fi Pineapple or a web server.
2. **Configure Redirects**: Ensure that all HTTP requests are redirected to `index.php`.
3. **Conduct the Test**: Users will be prompted to enter their Wi-Fi password under the guise of a firmware update.
4. **Analyze the Results**: Review the `.logs` file to evaluate the captured credentials and assess the effectiveness of the phishing simulation.

## Ethical Considerations

This project is intended for **ethical penetration testing** purposes only. It must be used in environments where you have **explicit permission** to conduct such tests. All data captured during the simulation should be handled responsibly and securely deleted after testing.

This project is a valuable tool for security professionals seeking to enhance their organization’s defenses against phishing attacks and improve user training on recognizing such threats.

## Disclaimer

The creators of this project are not responsible for any misuse. The **Evil-Wi-Fi Phishing Simulation** should be used solely for educational purposes and to improve security practices within authorized environments.
