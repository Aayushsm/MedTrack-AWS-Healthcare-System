# MedTrack: AWS Cloud-Enabled Healthcare Management System

A cloud-native healthcare management platform deployed on AWS EC2, featuring role-based access for patients and doctors, DynamoDB persistence, and automated SNS event alerts.

## Architecture Overview
- **Compute & Hosting:** AWS EC2 (Amazon Linux 2023), Nginx Reverse Proxy, Gunicorn WSGI
- **Backend:** Python (Flask), Boto3
- **Database:** Amazon DynamoDB (`MedTrack_Users`, `MedTrack_Appointments`, `MedTrack_Records`)
- **Security:** AWS IAM Instance Profile (`MedTrack-EC2-Role`) — no hardcoded AWS credentials
- **Notifications:** Amazon Simple Notification Service (SNS)
- **Monitoring:** AWS CloudWatch (CPU Utilization alarms)

## Live Deployment
- Public IP / Endpoint: `http://65.1.94.131`
