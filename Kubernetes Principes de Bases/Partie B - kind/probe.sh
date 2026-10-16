#!/bin/bash
# Availability probe: query the web-app service every 0.2 s while an update runs.
# usage: probe.sh <command that triggers the update>
kubectl delete pod probe --ignore-not-found >/dev/null
kubectl run probe --image=curlimages/curl --restart=Never -- \
  sh -c 'for i in $(seq 1 150); do c=$(curl -s -m 1 -o /dev/null -w "%{http_code}" http://web-app); echo "$(date +%T) $c"; sleep 0.2; done' >/dev/null
kubectl wait --for=condition=Ready pod/probe --timeout=60s >/dev/null
sleep 3
eval "$1"
kubectl rollout status deployment/web-app
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/probe --timeout=120s >/dev/null
kubectl logs probe > /tmp/probe.txt
echo "--- résultat de la sonde ---"
echo "réponses 200 : $(grep -c ' 200$' /tmp/probe.txt)"
echo "échecs (000) : $(grep -c ' 000$' /tmp/probe.txt)"
