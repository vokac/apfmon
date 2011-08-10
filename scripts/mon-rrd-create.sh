#
# update the RRD for PYF. Count states for all queues
#

# Loop over all panda queues (qid), note qid=0 will return
# a count for all queues

# 1 minute samples
# day: 1 averaged, store 1440
# week: 5 averaged (5m), store 2016
# month: 60 averaged (1h), store 720
# year: 360 averaged (6h), store 1460
# 900 s (15min) heartbeat

fids=`curl --connect-timeout 3 -fks -m 5 http://localhost/mon/f/`
[ $? -ne 0 ] && ( echo FAIL rrd-create f; exit 1 )
qids=`curl --connect-timeout 3 -fks -m 5 http://localhost/mon/r/`
[ $? -ne 0 ] && ( echo FAIL rrd-create r; exit 1 )

for f in 0 $fids; do
  # test for integer
  [ $f -eq $f ] || ( echo Bad fid:; break )

  for q in 0 $qids; do
    # test for integer
    [ $q -eq $q ] || ( echo Bad qid:; break )
  
    db=/var/tmp/rrd/job-state-$f-$q.rrd
    if [ -f $db ]; then 
      continue
    fi
  
    echo Creating $db
    rrdtool create $db               \
              --step 60               \
              --start `date +%s`       \
              DS:created:GAUGE:900:U:U  \
              DS:running:GAUGE:900:U:U   \
              DS:exiting:GAUGE:900:U:U    \
              DS:fault:GAUGE:900:U:U       \
              DS:done:GAUGE:900:U:U         \
              RRA:AVERAGE:0.5:1:1440         \
              RRA:AVERAGE:0.5:5:2016          \
              RRA:AVERAGE:0.5:60:720           \
              RRA:AVERAGE:0.5:360:1460
  done

done
