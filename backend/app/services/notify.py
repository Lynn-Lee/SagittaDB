"""
通知服务（Pack E）。
支持：钉钉 / 企业微信 / 飞书 / 邮件 四个通知渠道。
触发时机：工单提交、审批通过/驳回、执行完成/异常、工单取消。
配置来源：SystemConfig 表（system_config_service）。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
import urllib.parse
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# 工单状态 → 通知标题和颜色
STATUS_NOTICE = {
    0: ("📋 工单待审核", "#1558A8"),
    1: ("❌ 工单已驳回", "#f5222d"),
    2: ("✅ 工单审核通过", "#52c41a"),
    6: ("🎉 工单执行成功", "#52c41a"),
    7: ("⚠️ 工单执行异常", "#fa8c16"),
    8: ("🚫 工单已取消", "#AEAEB2"),
}

STATUS_DESC = {
    0: "待审核", 1: "审批驳回", 2: "审核通过",
    3: "定时执行", 4: "队列中", 5: "执行中",
    6: "执行成功", 7: "执行异常", 8: "已取消",
}


class NotifyService:
    """统一通知入口，根据系统配置决定发往哪些渠道。"""

    def __init__(self, config: dict[str, str]):
        """
        config: SystemConfig 中的配置值字典，key 为 config_key。
        由调用方从数据库加载后传入。
        """
        self.config = config

    @staticmethod
    async def notify_workflow(
        db,
        workflow_id: int,
        workflow_name: str,
        status: int,
        operator: str,
        instance_name: str = "",
        db_name: str = "",
        remark: str = "",
    ) -> None:
        """
        工单状态变更通知入口。
        由 workflow router 在审批/执行完成后调用。
        """
        from app.services.system_config import SystemConfigService

        async def get(key: str) -> str:
            return await SystemConfigService.get_value(db, key)

        config = {
            "ding_webhook":    await get("ding_webhook"),
            "ding_secret":     await get("ding_secret"),
            "ding_enabled":    await get("ding_enabled"),
            "wecom_webhook":   await get("wecom_webhook"),
            "wecom_enabled":   await get("wecom_enabled"),
            "feishu_webhook":  await get("feishu_webhook"),
            "feishu_enabled":  await get("feishu_enabled"),
            "mail_host":       await get("mail_host"),
            "mail_user":       await get("mail_user"),
            "mail_password":   await get("mail_password"),
            "mail_port":       await get("mail_port"),
            "mail_use_ssl":    await get("mail_use_ssl"),
            "platform_url":    await get("platform_url"),
        }

        svc = NotifyService(config)
        title, color = STATUS_NOTICE.get(status, ("📋 工单状态变更", "#1558A8"))

        content_lines = [
            f"**{title}**",
            f"工单名称：{workflow_name}",
            f"工单ID：#{workflow_id}",
            f"状态：{STATUS_DESC.get(status, '未知')}",
            f"操作人：{operator}",
        ]
        if instance_name:
            content_lines.append(f"目标实例：{instance_name}")
        if db_name:
            content_lines.append(f"数据库：{db_name}")
        if remark:
            content_lines.append(f"备注：{remark}")
        content_lines.append(f"时间：{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")

        platform_url = config.get("platform_url", "http://localhost")
        detail_url = f"{platform_url}/workflow/{workflow_id}"
        content_lines.append(f"[查看详情]({detail_url})")

        content = "\n".join(content_lines)

        # 并发发送所有启用的渠道（忽略单个渠道失败）
        import asyncio
        tasks = []
        if config.get("ding_enabled") == "true" and config.get("ding_webhook"):
            tasks.append(svc._send_dingtalk(title.replace("**", ""), content))
        if config.get("wecom_enabled") == "true" and config.get("wecom_webhook"):
            tasks.append(svc._send_wecom(title.replace("**", ""), content))
        if config.get("feishu_enabled") == "true" and config.get("feishu_webhook"):
            tasks.append(svc._send_feishu(title.replace("**", ""), content))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.warning("notify_channel_%d_failed: %s", i, str(r))

    # ── 钉钉 ──────────────────────────────────────────────────

    async def _send_dingtalk(self, title: str, content: str) -> dict:
        import httpx
        webhook = self.config.get("ding_webhook", "")
        secret = self.config.get("ding_secret", "")

        url = webhook
        if secret:
            ts = str(round(time.time() * 1000))
            sign_str = f"{ts}\n{secret}"
            sign = base64.b64encode(
                hmac.new(secret.encode(), sign_str.encode(), digestmod=hashlib.sha256).digest()
            ).decode()
            url = f"{webhook}&timestamp={ts}&sign={urllib.parse.quote_plus(sign)}"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content,
            },
            "at": {"isAtAll": False},
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()

        if data.get("errcode") != 0:
            raise Exception(f"钉钉通知失败：{data.get('errmsg', '未知错误')}")
        logger.info("dingtalk_notify_sent: %s", title)
        return data

    # ── 企业微信 ──────────────────────────────────────────────

    async def _send_wecom(self, title: str, content: str) -> dict:
        import httpx
        webhook = self.config.get("wecom_webhook", "")

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            },
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook, json=payload)
            data = resp.json()

        if data.get("errcode") != 0:
            raise Exception(f"企微通知失败：{data.get('errmsg', '未知错误')}")
        logger.info("wecom_notify_sent: %s", title)
        return data

    # ── 飞书 ──────────────────────────────────────────────────

    async def _send_feishu(self, title: str, content: str) -> dict:
        import httpx
        webhook = self.config.get("feishu_webhook", "")

        # 飞书 Webhook 支持 Markdown（富文本）
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": content},
                    }
                ],
            },
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook, json=payload)
            data = resp.json()

        code = data.get("code") or data.get("StatusCode")
        if code and code != 0:
            raise Exception(f"飞书通知失败：{data}")
        logger.info("feishu_notify_sent: %s", title)
        return data

    # ── 邮件（可选，配置完整时发送）────────────────────────────

    async def _send_mail(self, subject: str, content: str, to_emails: list[str]) -> None:
        import smtplib
        from email.mime.text import MIMEText

        host = self.config.get("mail_host", "")
        port = int(self.config.get("mail_port", "465"))
        use_ssl = self.config.get("mail_use_ssl", "true").lower() == "true"
        user = self.config.get("mail_user", "")
        password = self.config.get("mail_password", "")

        if not host or not user or not to_emails:
            return

        msg = MIMEText(content.replace("\n", "<br>").replace("**", "<b>").replace("**", "</b>"),
                       "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = ", ".join(to_emails)

        if use_ssl:
            smtp = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            smtp = smtplib.SMTP(host, port, timeout=10)
            smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(user, to_emails, msg.as_string())
        smtp.quit()
        logger.info("mail_notify_sent: subject=%s to=%s", subject, to_emails)
