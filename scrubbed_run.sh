PAYLOAD=$(python3 ~/fhockey_21/daily_updates.py); DATA_START='{"channel":"XXXXXXXX", "text":"'; DATA_END='"}'; curl -X POST -H 'Authorization: Bearer yeah-RightImGonnaCheckInARealToken' -H 'Content-type: application/json' --data "$DATA_START$PAYLOAD$DATA_END" https://slack.com/api/chat.postMessage;

# dev channel id: XXXXXXX
# prod channel id: XXXXXXXX
