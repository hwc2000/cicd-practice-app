pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'RUN_DEPLOY',
            defaultValue: false,
            description: 'Run deployment to vm1. Keep false until the deploy server is ready.'
        )
    }

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
                sh '''
                    . .venv/bin/activate
                    set +e
                    PYTHONPATH=. pytest -q > pytest-output.log 2>&1
                    test_status=$?
                    cat pytest-output.log
                    exit $test_status
                '''
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
                expression {
                    params.RUN_DEPLOY && (!env.BRANCH_NAME || env.BRANCH_NAME == 'main')
                }
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
        failure {
            sh '''
                set +e
                {
                    echo "# Debug Agent Input"
                    echo
                    echo "## Build"
                    echo "- Job: ${JOB_NAME}"
                    echo "- Build number: ${BUILD_NUMBER}"
                    echo "- Branch: ${BRANCH_NAME:-unknown}"
                    echo "- Commit: ${GIT_COMMIT:-unknown}"
                    echo
                    echo "## Recent Commit"
                    git log -1 --oneline
                    echo
                    echo "## Changed Files"
                    if git rev-parse HEAD~1 >/dev/null 2>&1; then
                        git diff --name-only HEAD~1..HEAD
                    else
                        git show --name-only --format="" HEAD
                    fi
                    echo
                    echo "## Recent Diff"
                    if git rev-parse HEAD~1 >/dev/null 2>&1; then
                        git diff --stat HEAD~1..HEAD
                    else
                        git show --stat --format="" HEAD
                    fi
                    echo
                    echo "## Pytest Output"
                    if [ -f pytest-output.log ]; then
                        cat pytest-output.log
                    else
                        echo "pytest-output.log not found"
                    fi
                } > debug-agent-input.md
                python3 scripts/debug_agent.py --input debug-agent-input.md --output debug-agent-report.md
                exit 0
            '''
            archiveArtifacts artifacts: 'debug-agent-input.md, debug-agent-report.md, pytest-output.log', allowEmptyArchive: true
            echo 'CI/CD pipeline failed. Debug Agent input and report were archived.'
        }
        success {
            echo 'CI/CD pipeline succeeded.'
        }
    }
}
