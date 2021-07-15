:local serverUrl "http://192.168.210.2:8080"
:local countrys {"US";"CN";"HK"}
:local addressTypes {"ipv4";"ipv6"}
:global lastNicUpdateTime
:foreach country in=$countrys do={
    :foreach addressType in=$addressTypes do={
        :global lastNicUpdateTime ""
        :if ([:file find name=("nic_".$addressType."_".$country.".txt")]) do={
            :global lastNicUpdateTime [:file get ("nic_".$addressType."_".$country) contents]
        }
        :put $lastNicUpdateTime   
        :local srcUrl ($serverUrl."/ros?"."country=".$country."&type=".$addressType."&lastTime=".$lastNicUpdateTime)
        :local httpResult [/tool fetch mode=http url=$srcUrl as-value dst-path=($country."_".$addressType.".rsc")]
        :if ($httpResult->"status" = "finished") do={
            :log info messag=[:put ("download ".$country."_".$addressType.".rsc"." success!")]
            :import file-name=($country."_".$addressType.".rsc")
        } else={
            :log error messag=[:put ("download ".$country."_".$addressType.".rsc"." fail!")]
        }
    }
}

