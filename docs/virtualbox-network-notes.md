# VirtualBox Network Notes

이 문서는 현재 병행 중인 두 흐름을 헷갈리지 않게 분리하기 위한 메모입니다.

## 두 실습의 구분

### 1. cicd-practice-app / CI-CD Agent 실험

목표:

```text
GitHub
-> Jenkins
-> pytest / Docker build
-> 실패 artifact 생성
-> Debug Agent / LangGraph / harness 실험
```

현재 이 저장소의 중심 작업입니다.

중요한 것:

```text
Jenkins job
Jenkinsfile
debug-agent-input.md
pytest-output.log
debug-agent-report.md
scripts/debug_agent.py
scripts/run_debug_graph.py
```

### 2. 강사님 k3s / VM 네트워크 실습

목표:

```text
VirtualBox VM 네트워크 고정
나중에 컨테이너 기반 k3s 실습
```

이 흐름은 CI-CD Agent와 연결될 수 있지만, 지금은 별도 트랙으로 봅니다.

중요한 것:

```text
VirtualBox Adapter 설정
Host-only 고정 IP
NAT / Bridged 차이
netplan
나중의 k3s 실습 네트워크
```

## 현재 VM 공유 상태

현재는 k3s 전용 VM을 새로 만든 상태가 아닙니다.

지금은 같은 `jenkins-server` VM을 아래 두 흐름에서 함께 사용하고 있습니다.

```text
jenkins-server
= Jenkins CI 서버
= CI/CD Agent 실험 서버
= VirtualBox 네트워크 설정 실습 대상
= 나중 k3s 실습과 연결될 수 있는 네트워크 기준점
```

주의:

```text
나중에 k3s 전용 VM, WSL 기반 k3s, k3d, kind 같은 별도 환경을 만들면
jenkins-server와 k3s 실행 위치를 문서에서 다시 분리한다.
```

## 현재 jenkins-server 네트워크 구성

현재 `jenkins-server` VM은 아래처럼 사용합니다.

```text
Adapter 1: Bridged Adapter
Adapter 2: Host-only Adapter
Docker: docker0 bridge
```

현재 확인된 IP:

```text
192.168.0.18
= Adapter 1, Bridged Adapter
= 공유기 네트워크에서 받은 IP
= 바뀔 수 있음

192.168.56.10
= Adapter 2, Host-only Adapter
= 고정 접속용 IP
= WSL/Windows에서 SSH와 Jenkins 웹 접속에 사용

172.17.0.1
= Docker bridge IP
= SSH/Jenkins 접속용이 아님
= 보통 무시
```

앞으로 접속 기준은 아래 IP로 고정합니다.

```bash
ssh kyung@192.168.56.10
```

Jenkins 웹:

```text
http://192.168.56.10:8080
```

## NAT, Bridged, Host-only 역할

### NAT

역할:

```text
VM 인터넷 다운로드용
apt install / apt update 때 안정적이고 빠른 경우가 많음
```

특징:

```text
VM이 VirtualBox 뒤에서 인터넷을 사용
외부에서 VM으로 바로 접속하기는 불편함
포트 포워딩을 설정하면 SSH/Jenkins 접속 가능
```

현재 판단:

```text
apt 설치가 느릴 때는 Adapter 1을 NAT로 바꿔서 설치하는 방식이 좋음
설치가 끝나면 다시 Bridged + Host-only 구성으로 돌아와도 됨
```

### Bridged Adapter

역할:

```text
VM을 공유기 네트워크의 독립된 컴퓨터처럼 붙임
```

현재 IP:

```text
192.168.0.18
```

특징:

```text
브라우저와 SSH 접속이 직관적
공유기 DHCP라 IP가 바뀔 수 있음
Wi-Fi 환경에서는 VirtualBox 브리지가 느리거나 불안정할 수 있음
```

### Host-only Adapter

역할:

```text
Windows/WSL host와 VM 사이의 고정 관리 네트워크
```

현재 고정 IP:

```text
192.168.56.10
```

특징:

```text
인터넷용이 아님
고정 SSH/Jenkins 접속용으로 사용
default route를 잡지 않는 것이 안전함
```

## Netplan 설정

Host-only 어댑터는 `enp0s8`로 잡혀 있다고 보고 아래처럼 설정합니다.

파일:

```text
/etc/netplan/02-hostonly.yaml
```

내용:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s8:
      dhcp4: no
      addresses:
        - 192.168.56.10/24
```

적용:

```bash
sudo netplan apply
```

확인:

```bash
hostname -I
ip a
ip route
```

정상 예:

```text
hostname -I
192.168.0.18 192.168.56.10 172.17.0.1
```

## 중요한 주의점

Host-only 어댑터에는 아래 설정을 넣지 않는 것이 좋습니다.

```yaml
routes:
  - to: default
    via: 192.168.56.1
```

이유:

```text
192.168.56.1은 Host-only 네트워크의 host 쪽 주소입니다.
Host-only는 인터넷 출구로 쓰는 네트워크가 아닙니다.
여기에 default route를 잡으면 apt, GitHub, Jenkins plugin download 등이 꼬일 수 있습니다.
```

`ip route`에서 아래처럼 보이면 좋지 않습니다.

```text
default via 192.168.56.1 dev enp0s8
```

default route는 Bridged 또는 NAT 쪽에 있어야 합니다.

예:

```text
default via 192.168.0.1 dev enp0s3
```

또는 NAT를 쓸 때:

```text
default via 10.0.2.2 dev enp0s3
```

## 작업할 때 추천 방식

### apt 설치가 너무 느릴 때

```text
VM shutdown
-> VirtualBox Network
-> Adapter 1을 NAT로 변경
-> VM boot
-> apt update / apt install
-> 필요하면 다시 shutdown
-> Adapter 1을 Bridged로 복구
```

Host-only Adapter 2는 그대로 유지합니다.

### 평소 CI/CD Agent 실습할 때

```text
Adapter 1: Bridged
Adapter 2: Host-only
SSH: 192.168.56.10
Jenkins: http://192.168.56.10:8080
```

### 나중에 k3s 실습할 때

k3s의 Kubernetes 네트워크와 Jenkins VM 관리 IP는 분리해서 생각합니다.

```text
192.168.56.10
= Jenkins VM 관리 IP
= SSH/Jenkins 웹 접속용

k3s Pod/Service/Container network
= 나중에 별도 실습에서 다룰 네트워크
```

처음부터 Jenkins VM IP와 k3s 내부 Kubernetes 네트워크를 섞어 생각하지 않습니다.
