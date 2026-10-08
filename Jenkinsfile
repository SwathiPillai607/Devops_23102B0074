pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    python3 -m pytest -v --junitxml=reports/test-results.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/*.xml'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t beneficiary-portal:${BUILD_NUMBER} .
                    docker tag beneficiary-portal:${BUILD_NUMBER} beneficiary-portal:latest
                '''
            }
        }

        stage('Deploy Staging Container') {
            steps {
                sh '''
                    docker stop beneficiary-portal-staging || true
                    docker rm beneficiary-portal-staging || true
                    docker run -d --name beneficiary-portal-staging -p 8080:8000 beneficiary-portal:latest
                '''
            }
        }
    }

    post {
        success {
            echo "CI/CD Pipeline executed successfully!"
        }
        failure {
            echo "Pipeline failed. Review build stage logs."
        }
    }
}