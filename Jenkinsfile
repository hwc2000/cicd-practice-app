pipeline {
    agent any

    environment {
        IMAGE_NAME = 'cicd-practice-app'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        DEPLOY_HOST = 'CHANGE_ME_DEPLOY_SERVER_IP'
        DEPLOY_USER = 'CHANGE_ME_USER'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install') {
            steps {
                sh 'python3 -m venv .venv'
                sh '. .venv/bin/activate && pip install -r requirements-dev.txt'
            }
        }

        stage('Test') {
            steps {
                sh '. .venv/bin/activate && pytest -q'
            }
        }

        stage('Build Image') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .'
                sh 'docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest'
                sh 'docker save ${IMAGE_NAME}:latest -o ${IMAGE_NAME}.tar'
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sshagent(credentials: ['deploy-server-ssh-key']) {
                    sh '''
                        scp ${IMAGE_NAME}.tar ${DEPLOY_USER}@${DEPLOY_HOST}:/tmp/${IMAGE_NAME}.tar
                        scp scripts/deploy.sh ${DEPLOY_USER}@${DEPLOY_HOST}:/tmp/deploy-cicd-practice-app.sh
                        ssh ${DEPLOY_USER}@${DEPLOY_HOST} 'bash /tmp/deploy-cicd-practice-app.sh'
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'CI/CD pipeline succeeded.'
        }
        failure {
            echo 'CI/CD pipeline failed. Check console logs.'
        }
    }
}
