pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'RUN_DEPLOY',
            defaultValue: false,
            description: 'Run deployment to vm1. Keep false until the deploy server is ready.'
        )
        booleanParam(
            name: 'AUTOFIX_ENABLED',
            defaultValue: false,
            description: 'Enable auto-fix on test failure. Agent will fix code, commit, push, and re-trigger build.'
        )
        booleanParam(
            name: 'OPENAI_DEBUG_AGENT_ENABLED',
            defaultValue: false,
            description: 'Enable optional OpenAI-backed debug report on failure.'
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
                if [ -x .venv/bin/python ]; then
                    . .venv/bin/activate
                    PYTHON_BIN=python
                else
                    PYTHON_BIN=python3
                fi
                "$PYTHON_BIN" scripts/debug_agent.py --input debug-agent-input.md --output debug-agent-report.md
                "$PYTHON_BIN" scripts/run_debug_graph.py --input debug-agent-input.md --output debug-graph-state.json
                "$PYTHON_BIN" scripts/run_langgraph_debug.py --input debug-agent-input.md --output debug-langgraph-state.json
                "$PYTHON_BIN" scripts/compare_graph_states.py --local debug-graph-state.json --langgraph debug-langgraph-state.json --output debug-graph-compare.json
                exit 0
            '''
            script {
                // --- Auto-Fix ---
                if (params.AUTOFIX_ENABLED) {
                    def autofixExitCode = 1
                    try {
                        withCredentials([string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY')]) {
                            autofixExitCode = sh(
                                script: '''
                                    set +e
                                    if [ -x .venv/bin/python ]; then
                                        . .venv/bin/activate
                                        PYTHON_BIN=python
                                    else
                                        PYTHON_BIN=python3
                                    fi
                                    PYTHONPATH=. OPENAI_DEBUG_AGENT_ENABLED=true "$PYTHON_BIN" scripts/run_autofix.py \
                                        --input debug-agent-input.md \
                                        --workspace . \
                                        --output autofix-result.json \
                                        --max-attempts 3
                                ''',
                                returnStatus: true
                            )
                        }
                    } catch (Exception e) {
                        echo "OpenAI credential not available. Running auto-fix with rule-based only."
                        autofixExitCode = sh(
                            script: '''
                                set +e
                                if [ -x .venv/bin/python ]; then
                                    . .venv/bin/activate
                                    PYTHON_BIN=python
                                else
                                    PYTHON_BIN=python3
                                fi
                                PYTHONPATH=. "$PYTHON_BIN" scripts/run_autofix.py \
                                    --input debug-agent-input.md \
                                    --workspace . \
                                    --output autofix-result.json \
                                    --max-attempts 3
                            ''',
                            returnStatus: true
                        )
                    }

                    if (autofixExitCode == 0 && fileExists('autofix-result.json')) {
                        echo 'Auto-fix succeeded! Committing and pushing fix...'
                        withCredentials([usernamePassword(
                            credentialsId: 'github-token',
                            usernameVariable: 'GIT_USER',
                            passwordVariable: 'GIT_TOKEN'
                        )]) {
                            sh '''
                                set +e
                                git config user.email "autofix-agent@ci.local"
                                git config user.name "CI AutoFix Agent"
                                git checkout main || git checkout -b main
                                git add -A
                                git commit -m "autofix: fix build #${BUILD_NUMBER}"
                                git push https://${GIT_USER}:${GIT_TOKEN}@github.com/hwc2000/cicd-practice-app.git main
                            '''
                        }
                        // Trigger verification rebuild
                        build job: env.JOB_NAME, parameters: [
                            booleanParam(name: 'AUTOFIX_ENABLED', value: false),
                            booleanParam(name: 'RUN_DEPLOY', value: false),
                            booleanParam(name: 'OPENAI_DEBUG_AGENT_ENABLED', value: false)
                        ], wait: false
                    } else {
                        echo 'Auto-fix could not resolve the failure. Manual review required.'
                    }
                } else {
                    echo 'AUTOFIX_ENABLED=false, skipping auto-fix.'
                }

                // --- Optional OpenAI Debug Report (when auto-fix is off) ---
                if (params.OPENAI_DEBUG_AGENT_ENABLED && !params.AUTOFIX_ENABLED) {
                    withCredentials([string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY')]) {
                        sh '''
                            set +e
                            if [ -x .venv/bin/python ]; then
                                . .venv/bin/activate
                                PYTHON_BIN=python
                            else
                                PYTHON_BIN=python3
                            fi
                            PYTHONPATH=. OPENAI_DEBUG_AGENT_ENABLED=true "$PYTHON_BIN" scripts/run_openai_debug_agent.py --input debug-agent-input.md --output debug-openai-report.md
                            PYTHONPATH=. OPENAI_DEBUG_AGENT_ENABLED=true "$PYTHON_BIN" scripts/run_openai_debug_agent.py --input debug-agent-input.md --output debug-openai-report.json --format json
                            exit 0
                        '''
                    }
                }
            }
            archiveArtifacts artifacts: 'debug-agent-input.md, debug-agent-report.md, debug-graph-state.json, debug-langgraph-state.json, debug-graph-compare.json, debug-openai-report.md, debug-openai-report.json, autofix-result.json, pytest-output.log', allowEmptyArchive: true
            echo 'CI/CD pipeline failed. Debug artifacts were archived.'
        }
        success {
            echo 'CI/CD pipeline succeeded.'
        }
    }
}
