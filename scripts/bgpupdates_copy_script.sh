#!/bin/sh

updates=$(sudo docker ps | grep rnode | grep -v net0 | grep -v 11872 | awk '{print $NF}')

mkdir -p bgpupdates/ || true
echo `date`
for cont in ${updates}; do
    echo "Fetching updates file from ${cont}"
    year_month=`date +%Y.%m`
    filename=`date +%Y%m%d.%k%M`
    mkdir -p bgpupdates/${cont}/${year_month}/
    sudo docker cp ${cont}:/tmp/bird-mrtdump_bgp bgpupdates/${cont}/${year_month}/updates.${filename}
done
