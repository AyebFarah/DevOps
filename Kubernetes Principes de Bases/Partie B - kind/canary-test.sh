#!/bin/bash
# Canary test: 100 requests to the web-app service, count v1 / v2 answers.
kubectl delete pod canary-test --ignore-not-found >/dev/null
kubectl run canary-test --image=curlimages/curl --restart=Never -- \
  sh -c 'for i in $(seq 1 100); do curl -s http://web-app; echo; done' >/dev/null
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/canary-test --timeout=120s >/dev/null
kubectl logs canary-test > /tmp/canary.txt
echo "v1 (It works!) : $(grep -c '<title>It works' /tmp/canary.txt)"
echo "v2 (canary)    : $(grep -c 'v2 canary' /tmp/canary.txt)"
