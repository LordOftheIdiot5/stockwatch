"""Notify on failed production workflows without reading their logs or artifacts."""
from __future__ import annotations
import json,os,re,time
from pathlib import Path
from notify import send,escape

WATCHED={"Scan","Deploy dashboard","Refresh official open data","Stockwatch production health",
"Private exchange archive","Private daily observation archive","Official delayed exchange availability"}
FAILURES={"failure","timed_out","startup_failure","action_required","stale","cancelled"}
def message(event,repo):
    run=event.get("workflow_run",{})
    if not isinstance(run,dict):return None
    if run.get("head_branch")!="main" or (run.get("head_repository") or {}).get("full_name")!=repo:return None
    if run.get("event") not in {"push","schedule","workflow_dispatch"} or run.get("name") not in WATCHED:return None
    if run.get("conclusion") not in FAILURES:return None
    rid=run.get("id");attempt=run.get("run_attempt",1)
    if type(rid)!=int or rid<1 or type(attempt)!=int or attempt<1 or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repo):raise ValueError("invalid run identity")
    return ("Nordl Stockwatch — production workflow "+run["conclusion"]+"\n"+
            run["name"]+" · attempt "+str(attempt)+"\n"+
            "https://github.com/"+repo+"/actions/runs/"+str(rid)+"\n"+
            "Inspect the failed job and rerun only after the cause is understood.")
def deliver(text,token,chat,send_fn=send,pause=time.sleep):
    if not token or not chat:raise RuntimeError("Telegram credentials missing")
    for i in range(3):
        if send_fn(token,chat,escape(text)):return True
        if i<2:pause(5*(i+1))
    raise RuntimeError("Telegram delivery failed after retries")
def main():
    event=json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch":
        text="Nordl Stockwatch — independent workflow alert test. No production failure simulated."
    else:text=message(event,os.environ["GITHUB_REPOSITORY"])
    if not text:
        print("No eligible production workflow failure.")
        return
    deliver(text,os.getenv("TELEGRAM_BOT_TOKEN"),os.getenv("TELEGRAM_CHAT_ID"))
    print("Telegram accepted notification.")
if __name__=="__main__":main()
