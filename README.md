# HomeLane Design Platform

HomeLane Design Platform is a Flask-based web application that facilitates interaction between clients and designers for home design projects. It integrates with AWS services such as S3, DynamoDB, and RDS MySQL for data storage and management.

## Features

- **User Authentication**: Secure login for clients and designers.
- **File Upload and Management**: Leverage AWS S3 for efficient file handling.
- **Client-Designer Project Assignment**: Seamlessly assign projects.
- **Real-Time Messaging**: Instant communication between clients and designers.
- **Product Management**: Manage design project details effectively.

## Prerequisites

- Python 3.x
- AWS account with access to S3, DynamoDB, and RDS
- MySQL database

## Installation

1. **Clone the Repository:**
   ```sh
   git clone https://github.com/Invictus-2305/HomeLane.git
   cd HomeLane
   ```

2. **Install Required Packages:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Set Up AWS Services:**
   - S3 bucket
   - DynamoDB tables
   - RDS MySQL database

4. **Update Configuration in `app.py`:**
   - Set your AWS region
   - Configure your S3 bucket name
   - Update DynamoDB table names
   - Set your MySQL database credentials

## Usage

Run the application:
```sh
python app.py
```
The application will start on `http://0.0.0.0:9000`.

## Main Routes

- `/` : Login and signup page
- `/client-registration` : Client registration page
- `/designer-registration` : Designer registration page
- `/clda/<email>` : Client dashboard
- `/deda` : Designer dashboard
- `/designer-home` : Designer home page

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).
