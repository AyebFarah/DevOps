#!/bin/bash
# Load-balancing test: follow web-app logs while 12 requests hit the service.
kubectl delete pod load-test --ignore-not-found >/dev/null
kubectl logs -l app=web-app -f --prefix --tail=0 --max-log-requests=10 > /tmp/weblogs.txt 2>&1 &
LOGPID=$!
sleep 4
kubectl run load-test --image=curlimages/curl --restart=Never -- \
  sh -c 'sleep 2; for i in $(seq 1 12); do curl -s -o /dev/null -w "requete $i -> %{http_code}\n" http://web-app; done' >/dev/null
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/load-test --timeout=90s >/dev/null
kubectl logs load-test > /tmp/load.txt
kubectl delete pod load-test >/dev/null
sleep 3
kill $LOGPID
wc -l /tmp/load.txt /tmp/weblogs.txt
cut -d" " -f1 /tmp/weblogs.txt | sort | uniq -c
