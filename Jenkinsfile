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
                if (params.OPENAI_DEBUG_AGENT_ENABLED) {
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
                            if [ -f debug-openai-report.json ]; then
                                PYTHONPATH=. "$PYTHON_BIN" scripts/apply_patch_candidate.py --input debug-openai-report.json --workspace . --apply --output patch-apply-result.json
                                git diff -- app tests > auto-fix.patch || true
                                if [ ! -s auto-fix.patch ]; then
                                    echo "No workspace diff was produced by patch candidate application." > auto-fix.patch
                                fi
                                if [ -f patch-apply-result.json ]; then
                                    set +e
                                    PYTHONPATH=. pytest -q > auto-fix-pytest.log 2>&1
                                    auto_fix_test_status=$?
                                    printf '%s' "$auto_fix_test_status" > .auto-fix-status
                                    cat auto-fix-pytest.log
                                    python - <<'PY'
import json
from pathlib import Path

result_path = Path("auto-fix-verification.json")
status = int(Path(".auto-fix-status").read_text(encoding="utf-8").strip())
result = {
    "verification_command": "PYTHONPATH=. pytest -q",
    "exit_code": status,
    "passed": status == 0,
    "log_file": "auto-fix-pytest.log",
}
result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
                                fi
                            fi
                            exit 0
                        '''
                    }
                } else {
                    echo 'OPENAI_DEBUG_AGENT_ENABLED=false, skipping optional OpenAI debug report.'
                }
            }
            archiveArtifacts artifacts: 'debug-agent-input.md, debug-agent-report.md, debug-graph-state.json, debug-langgraph-state.json, debug-graph-compare.json, debug-openai-report.md, debug-openai-report.json, patch-apply-result.json, auto-fix.patch, auto-fix-pytest.log, auto-fix-verification.json, pytest-output.log', allowEmptyArchive: true
            echo 'CI/CD pipeline failed. Debug Agent input, reports, graph states, optional OpenAI reports, auto-fix artifacts, and auto-fix verification artifacts were archived.'
        }
        success {
            echo 'CI/CD pipeline succeeded.'
        }
    }
}
