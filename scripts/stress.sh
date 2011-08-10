for i in `seq -w 1000`; do
  curl -F "cid=999999$i" -F "nick=NICK" -F "fid=peter-UK-test" -F "label=LABEL" http://localhost/mon/cr/
  curl -F "msg=no message here this is a stress test" -F "nick=NICK" -F "fid=peter-UK-test" -F "label=LABEL" http://localhost/mon/msg/
done
