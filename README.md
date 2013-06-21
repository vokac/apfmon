APFmon monitors ATLAS pilot factories
=====================================

APFmon is a django app which provides a monitoring window on pilot factory activity for the ATLAS experiment. It uses HTTP messaging to trace job states and provide views to help understand problems at the ~100 separate compute farms used by ATLAS. Some backend tools used are mysql, redis, memcached, d3js.
