# TP4 – GitOps, ArgoCD et Observabilité pour le Continuous Deployment

Réalisé par : Hanine BEN AMOR, Farah AYEB, Emna DRIHEM, Yasmine FERJANI – RT5, Groupe 1, INSAT (2026/2027).

Ce dossier est **l'unique source de vérité** (*Single Source of Truth*) du TP : l'application,
la stack d'observabilité et leur configuration sont décrites ici de façon déclarative, et
ArgoCD les applique en continu dans le cluster (modèle *pull*). Aucun `kubectl apply` manuel
n'est nécessaire après le bootstrap.

## Architecture

```
                 git push                       pull (toutes les 30 s)
 Développeur ──────────────► GitHub ◄──────────────────────────┐
                             AyebFarah/DevOps                    │
                             └─ GitOps-ArgoCD-Observabilite/     │
                                                                 │
 ┌──────────────────────────── cluster kind "tp4-gitops" ────────┼──────────────┐
 │  namespace argocd                                             │              │
 │   ArgoCD (server, repo-server, application-controller) ───────┘              │
 │     └─ Application "root"  (App-of-Apps → argocd/apps/)                      │
 │          ├─ AppProject tp4                                                   │
 │          ├─ podinfo-dev            → namespace podinfo-dev   (Kustomize)     │
 │          ├─ podinfo-prod           → namespace podinfo-prod  (Kustomize)     │
 │          ├─ kube-prometheus-stack  → namespace monitoring    (Helm 93.4.0)   │
 │          └─ monitoring-config      → namespace monitoring    (Kustomize)     │
 │                                                                              │
 │  Prometheus ── scrape ──► argocd-metrics / argocd-server-metrics /           │
 │      │                    argocd-repo-server / kube-state-metrics /          │
 │      │                    kubelet-cAdvisor / podinfo:9797/metrics            │
 │      ├──► règles d'alerte (PrometheusRule) ──► Alertmanager                  │
 │      └──► Grafana (dashboard "TP4 - GitOps, ArgoCD & Workloads")             │
 └──────────────────────────────────────────────────────────────────────────────┘
```

| Interface | URL (kind publie les NodePort sur localhost) |
|---|---|
| ArgoCD UI | http://localhost:30080 (anonyme = lecture seule, `admin` pour agir) |
| Grafana | http://localhost:30300 (anonyme = Viewer) |
| Prometheus | http://localhost:30090 |
| Alertmanager | http://localhost:30093 |
| podinfo (prod) | http://localhost:30898 |

## Arborescence

```
GitOps-ArgoCD-Observabilite/
├── apps/podinfo/
│   ├── base/                     Deployment, Service, ServiceMonitor (communs)
│   └── overlays/
│       ├── dev/                  1 réplica, image 6.17.0 (validation des nouvelles versions)
│       └── prod/                 3 réplicas, image 6.16.0, NodePort 30898, générateur de trafic
├── argocd/
│   ├── install/                  ArgoCD v3.6.1 + patchs (HTTP, anonyme lecture seule, NodePort)
│   ├── bootstrap/root-app.yaml   Application racine (App-of-Apps), appliquée une seule fois
│   └── apps/                     AppProject + 4 Applications filles
└── monitoring/
    ├── servicemonitors-argocd.yaml   scrape du control plane ArgoCD
    ├── prometheusrule-tp4.yaml       4 règles d'alerte
    ├── dashboards/tp4-gitops-dashboard.json   export JSON du dashboard Grafana
    └── kustomization.yaml            ConfigMap du dashboard (label grafana_dashboard=1)
```

## Choix techniques

- **podinfo** (microservice Go) : expose nativement `/metrics` (Prometheus), des sondes `/readyz` `/healthz`,
  un endpoint `/status/{code}` pour générer des erreurs, et des tags d'image versionnés.
- **Kustomize base + overlays** : une seule définition de l'application, les environnements ne
  surchargent que le nombre de réplicas, le tag d'image et l'exposition. Un déploiement = un commit
  modifiant `newTag` ou `count` dans `overlays/prod/kustomization.yaml`.
- **App-of-Apps** : seul `root-app.yaml` est appliqué à la main ; ArgoCD déploie ensuite tout le reste,
  y compris la stack d'observabilité (exigence « niveau ingénieur » du sujet).
- **Automated sync + `prune` + `selfHeal`** sur toutes les applications : Git est la seule source de vérité,
  toute dérive manuelle est annulée en quelques secondes.
- **`progressDeadlineSeconds: 60`** et **`maxUnavailable: 0`** : un rollout bloqué (image invalide) est
  signalé `Degraded` au bout d'une minute, sans jamais réduire la capacité servie (les anciens pods restent).
- **`ignoreDifferences` sur `.spec.syncPolicy.automated`** dans l'application racine : permet de
  suspendre temporairement l'auto-sync d'une application fille pour un rollback, sans que la racine
  (elle-même en self-heal) ne le réactive immédiatement.
- **Sécurité** : AppProject `tp4` restreignant dépôts et namespaces ; mot de passe Grafana hors de Git
  (secret `grafana-admin` créé au bootstrap) ; conteneurs non-root, *read-only root filesystem*,
  capabilities supprimées ; accès anonyme **en lecture seule** uniquement (pratique acceptable pour une
  démo locale, à désactiver en production au profit du SSO/OIDC).

## Bootstrap (une seule fois)

```bash
kind create cluster --config kind-config.yaml               # NodePort publiés sur localhost
kubectl create namespace argocd
kubectl apply --server-side --force-conflicts -k argocd/install
kubectl -n argocd rollout status deploy/argocd-server
kubectl create namespace monitoring
kubectl -n monitoring create secret generic grafana-admin \
  --from-literal=admin-user=admin --from-literal=admin-password='<mot-de-passe>'
kubectl apply -f argocd/bootstrap/root-app.yaml             # puis tout est piloté par Git
argocd admin initial-password -n argocd                      # mot de passe admin ArgoCD
```

## Requêtes PromQL utilisées

| Objectif | Requête |
|---|---|
| Applications Synced / OutOfSync | `count(argocd_app_info{sync_status="Synced"})` |
| Applications non saines | `count(argocd_app_info{health_status=~"Degraded\|Progressing\|Missing"})` |
| Tableau Sync/Health | `argocd_app_info` (instantané, format table) |
| Health dans le temps | `sum by (health_status) (argocd_app_info{name="podinfo-prod"})` |
| Historique des syncs | `sum by (name, phase) (increase(argocd_app_sync_total{name=~"podinfo.*"}[2m]))` |
| Appels Git | `sum by (request_type) (rate(argocd_git_request_total[2m]))` |
| Latence Git p95 | `histogram_quantile(0.95, sum by (le) (rate(argocd_git_request_duration_seconds_bucket[5m])))` |
| Réconciliation p95 | `histogram_quantile(0.95, sum by (le) (rate(argocd_app_reconcile_bucket[5m])))` |
| Pods désirés | `sum(kube_deployment_spec_replicas{namespace="$namespace", deployment="podinfo"})` |
| Pods disponibles | `sum(kube_deployment_status_replicas_available{namespace="$namespace", deployment="podinfo"})` |
| Pods indisponibles | `sum(kube_deployment_status_replicas_unavailable{namespace="$namespace", deployment="podinfo"})` |
| Conteneurs en attente | `sum by (reason) (kube_pod_container_status_waiting_reason{namespace="$namespace"} == 1)` |
| CPU par pod | `sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="$namespace", pod=~"podinfo-.*", container!=""}[2m]))` |
| Mémoire par pod | `sum by (pod) (container_memory_working_set_bytes{namespace="$namespace", pod=~"podinfo-.*", container!=""})` |
| Redémarrages | `sum by (pod) (increase(kube_pod_container_status_restarts_total{namespace="$namespace"}[10m]))` |
| Trafic HTTP | `sum by (status) (rate(http_request_duration_seconds_count{namespace="$namespace"}[1m]))` |
| Taux d'erreurs 5xx | `100 * sum(rate(http_request_duration_seconds_count{namespace="$namespace", status=~"5.."}[1m])) / sum(rate(http_request_duration_seconds_count{namespace="$namespace"}[1m]))` |

Annotations Grafana (corrélation GitOps ↔ métriques) : syncs
`changes(argocd_app_sync_total{name="podinfo-prod"}[1m]) > 0`, transitions d'état
`argocd_app_info{name="podinfo-prod"} unless argocd_app_info{name="podinfo-prod"} offset 1m`,
alertes `ALERTS{alertname=~"TP4.*", alertstate="firing"}`.

## Règles d'alerte (`monitoring/prometheusrule-tp4.yaml`)

| Alerte | Condition | Pendant |
|---|---|---|
| `TP4ArgoAppDegraded` (critical) | `max by (name, dest_namespace) (argocd_app_info{health_status="Degraded"}) == 1` | 2 min |
| `TP4ArgoAppOutOfSync` (warning) | `max by (name, dest_namespace) (argocd_app_info{sync_status="OutOfSync"}) == 1` | 2 min |
| `TP4PodImagePullError` (critical) | `max by (namespace, pod, container) (kube_pod_container_status_waiting_reason{reason=~"ErrImagePull\|ImagePullBackOff"}) == 1` | 2 min |
| `TP4PodCrashLooping` (critical) | `... {reason="CrashLoopBackOff"} == 1` | 2 min |

## Rapport et captures

- Rapport PDF : `TP4 Devops GitOps ArgoCD Observabilite Hanine BEN AMOR Farah AYEB Emna DRIHEM Yasmine FERJANI.pdf`
- Captures réelles (terminal et interfaces Web ArgoCD / Grafana / Prometheus / podinfo) : `captures/`

## Scénarios de démonstration

| # | Scénario | Action |
|---|---|---|
| 1 | Déploiement continu | commit : `overlays/prod` → `count: 4`, `newTag: 6.17.0` |
| 2 | Drift & self-heal | `kubectl -n podinfo-prod delete deployment podinfo` / `kubectl scale --replicas=1` |
| 3 | Sync vs Health | commit : `newTag: 0.0.0-inexistant` → `Synced` mais `Degraded` (`ErrImagePull`) |
| 4 | Rollback | onglet *History and Rollback* (auto-sync suspendu), puis `git revert` pour réaligner Git |
| 5 | Corrélation | Grafana : courbes Desired/Available, Health, syncs ; alertes `Pending` → `Firing` → `Normal` |
