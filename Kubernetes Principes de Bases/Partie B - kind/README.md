# TP2 DevOps – Kubernetes : Principes de base (Partie B)

Mise en pratique de Kubernetes sur un cluster **kind** à 3 nœuds (1 control-plane + 2 workers).

Réalisé par : Hanine BEN AMOR, Farah AYEB, Emna DRIHEM, Yasmine FERJANI – RT5, Groupe 1, INSAT (2026/2027).

## Environnement

- Windows 11 + WSL 2 (Ubuntu 24.04) + Docker Desktop
- kind v0.33.0, kubectl v1.37.1 (Kubernetes v1.37.0)

## Fichiers

| Fichier | Rôle | Partie du TP |
|---|---|---|
| `kind-config.yaml` | Cluster 1 control-plane + 2 workers, ports 80/443 publiés pour l'Ingress | 1 |
| `deployment.yaml` | Deployment `web-app` : 3 réplicas, `httpd:2.4`, sélecteur `app: web-app` | 2 |
| `metallb-pool.yaml` | Pool d'IP MetalLB pour les services LoadBalancer | 3 |
| `lbtest.sh` | Suit les logs des pods pendant 12 requêtes (équilibrage de charge) | 3 |
| `deployment-recreate.yaml` | Même déploiement avec la stratégie `Recreate` | 4 |
| `probe.sh` | Sonde de disponibilité (150 requêtes) pendant une mise à jour | 4 |
| `deployment-v2-canary.yaml` | Canary v2 (1 réplica, même label `app: web-app`) | 4 |
| `canary-test.sh` | 100 requêtes et répartition v1 / v2 | 4 |
| `multi-app.yaml` | Pod à 2 conteneurs (nginx + sidecar) + Service ClusterIP + Ingress | 5 |

## Rejouer le TP

```bash
# 1. Cluster
kind create cluster --name devops-tp --config kind-config.yaml
kubectl get nodes

# 2. Pod et Deployment
kubectl run nginx-pod --image=nginx:alpine
kubectl exec nginx-pod -- sh -c 'echo "<h1>Hello DevOps</h1>" > /usr/share/nginx/html/index.html'
kubectl port-forward pod/nginx-pod 8080:80          # http://localhost:8080
kubectl apply -f deployment.yaml
kubectl get pods -o wide

# 3. Services
kubectl expose deployment web-app --type=ClusterIP --port=80 --target-port=80
kubectl run test-pod --image=curlimages/curl --rm -i --restart=Never -- curl -s http://web-app
kubectl patch svc web-app -p '{"spec":{"type":"NodePort"}}'
kubectl patch svc web-app -p '{"spec":{"type":"LoadBalancer"}}'
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.16.1/config/manifests/metallb-native.yaml
kubectl wait -n metallb-system --for=condition=Ready pod --all --timeout=180s
kubectl apply -f metallb-pool.yaml
bash lbtest.sh

# 4. Stratégies de déploiement
kubectl set image deployment/web-app httpd=httpd:latest
kubectl rollout status deployment/web-app
bash probe.sh "kubectl apply -f deployment-recreate.yaml"
kubectl apply -f deployment-v2-canary.yaml
bash canary-test.sh

# 5. Ingress + application multi-conteneurs
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.15.1/deploy/static/provider/kind/deploy.yaml
kubectl patch deployment ingress-nginx-controller -n ingress-nginx -p '{"spec":{"template":{"spec":{"nodeSelector":{"ingress-ready":"true"}}}}}'
kubectl apply -f multi-app.yaml
curl http://localhost/
```

## Nettoyage

```bash
kind delete cluster --name devops-tp
```
