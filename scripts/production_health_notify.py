"""Maintain one production incident and retry Telegram until acknowledged."""
import hashlib,json,os,subprocess
from pathlib import Path
from workflow_alert import deliver
TITLE="Stockwatch production health incident"
def gh(*args):
    return subprocess.check_output(["gh",*args],text=True)
def main():
    data=json.loads(Path("production-health.json").read_text())
    active=[i for i in data["issues"] if i["severity"] in ("critical","warning")]
    signature=hashlib.sha256("|".join(sorted(i["severity"]+":"+i["code"] for i in active)).encode()).hexdigest()[:16]
    marker="<!-- health:"+signature+" -->"
    sent="<!-- telegram:"+signature+" -->"
    issues=json.loads(gh("issue","list","--state","open","--search",TITLE+" in:title","--json","number,title,body,url","--limit","30"))
    matches=[i for i in issues if i["title"]==TITLE]
    current=matches[0] if matches else None
    run=os.environ["GITHUB_SERVER_URL"]+"/"+os.environ["GITHUB_REPOSITORY"]+"/actions/runs/"+os.environ["GITHUB_RUN_ID"]
    token,chat=os.getenv("TELEGRAM_BOT_TOKEN"),os.getenv("TELEGRAM_CHAT_ID")
    if active:
        if current and marker in current["body"] and sent in current["body"]:return
        body="Production checks detected:\n\n"+"\n".join("- "+i["severity"]+" / "+i["code"]+": "+i["message"] for i in active)+"\n\n[Diagnostic run]("+run+")\n\n"+marker
        if current:
            number=str(current["number"]);url=current["url"]
            gh("issue","edit",number,"--body",body)
        else:
            url=gh("issue","create","--title",TITLE,"--body",body).strip()
            number=url.rsplit("/",1)[-1]
        deliver("Stockwatch production health ("+data["status"]+"): "+", ".join(i["code"] for i in active)+"\n"+url,token,chat)
        gh("issue","edit",number,"--body",body+"\n"+sent)
    elif current:
        # Close only after recovery notice succeeds; failed sends retry next check.
        deliver("Stockwatch production checks recovered. "+run,token,chat)
        gh("issue","close",str(current["number"]),"--comment","Production checks recovered. "+run)
if __name__=="__main__":main()
