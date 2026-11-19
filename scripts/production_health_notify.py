"""Maintain one actionable incident issue; only notify on changed incident signature."""
import hashlib,json,os,subprocess
from pathlib import Path
from notify import send,escape
TITLE="Stockwatch production health incident"
def gh(*args):
    return subprocess.check_output(["gh",*args],text=True)
def main():
    data=json.loads(Path("production-health.json").read_text())
    critical=[i for i in data["issues"] if i["severity"]=="critical"]
    # Warnings and known gaps remain visible in every run, not repeated incident alerts.
    signature=hashlib.sha256("|".join(sorted(i["code"] for i in critical)).encode()).hexdigest()[:16]
    issues=json.loads(gh("issue","list","--state","open","--search",TITLE+" in:title","--json","number,title,body,url","--limit","30"))
    matches=[i for i in issues if i["title"]==TITLE]
    current=matches[0] if matches else None
    run=os.environ["GITHUB_SERVER_URL"]+"/"+os.environ["GITHUB_REPOSITORY"]+"/actions/runs/"+os.environ["GITHUB_RUN_ID"]
    message=None
    if critical:
        body="Production checks detected:\n\n"+"\n".join("- "+i["code"]+": "+i["message"] for i in critical)+"\n\n[Diagnostic run]("+run+")\n\n<!-- health:"+signature+" -->"
        if current and "<!-- health:"+signature+" -->" in current["body"]:return
        if current:
            gh("issue","edit",str(current["number"]),"--body",body)
            gh("issue","comment",str(current["number"]),"--body","Incident changed. "+run)
            url=current["url"]
        else:url=gh("issue","create","--title",TITLE,"--body",body).strip()
        message="Stockwatch production health: "+", ".join(i["code"] for i in critical)+"\n"+url
    elif current:
        gh("issue","close",str(current["number"]),"--comment","Critical checks recovered. "+run)
        message="Stockwatch production checks recovered. "+run
    if message:
        token,chat=os.getenv("TELEGRAM_BOT_TOKEN"),os.getenv("TELEGRAM_CHAT_ID")
        if token and chat:
            if not send(token,chat,escape(message)):print("::warning::Telegram delivery failed; GitHub incident state retained")
        else:print("Telegram not configured; GitHub incident state retained")
if __name__=="__main__":main()
