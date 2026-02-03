"""
Turnstile 验证服务 - 处理 Cloudflare 验证
"""
import asyncio
import httpx
from typing import Optional
from app.core.config import setting
from app.core.logger import logger

class TurnstileManager:
    """Turnstile 验证管理器"""

    def __init__(self):
        self.yescaptcha_key = setting.grok_config.get("yescaptcha_key", "").strip()
        self.solver_url = setting.grok_config.get("turnstile_solver_url", "").strip()
        self.yescaptcha_api = "https://api.yescaptcha.com"
        # 默认 Grok SiteKey
        self.site_key = "0x4AAAAAAAhr9JGVDZbrZOo0"
        self.site_url = "https://grok.com"

    async def solve(self, url: Optional[str] = None, sitekey: Optional[str] = None) -> Optional[str]:
        """
        求解 Turnstile 验证
        
        Args:
            url: 触发验证的 URL
            sitekey: Turnstile SiteKey
            
        Returns:
            验证成功的 token，失败返回 None
        """
        url = url or self.site_url
        sitekey = sitekey or self.site_key
        
        try:
            if self.yescaptcha_key:
                return await self._solve_yescaptcha(url, sitekey)
            elif self.solver_url:
                return await self._solve_local(url, sitekey)
            else:
                logger.warning("[Turnstile] 未配置 YESCAPTCHA_KEY 或 TURNSTILE_SOLVER_URL")
                return None
        except Exception as e:
            logger.error(f"[Turnstile] 求解异常: {e}")
            return None

    async def _solve_yescaptcha(self, url: str, sitekey: str) -> Optional[str]:
        """使用 YesCaptcha 求解"""
        async with httpx.AsyncClient(timeout=60) as client:
            # 创建任务
            create_url = f"{self.yescaptcha_api}/createTask"
            payload = {
                "clientKey": self.yescaptcha_key,
                "task": {
                    "type": "TurnstileTaskProxyless",
                    "websiteURL": url,
                    "websiteKey": sitekey
                }
            }
            resp = await client.post(create_url, json=payload)
            data = resp.json()
            
            if data.get('errorId') != 0:
                logger.error(f"[Turnstile] YesCaptcha 创建任务失败: {data.get('errorDescription')}")
                return None
            
            task_id = data['taskId']
            
            # 轮询结果
            result_url = f"{self.yescaptcha_api}/getTaskResult"
            for _ in range(30):
                await asyncio.sleep(2)
                resp = await client.post(result_url, json={"clientKey": self.yescaptcha_key, "taskId": task_id})
                data = resp.json()
                
                if data.get('errorId') != 0:
                    logger.error(f"[Turnstile] YesCaptcha 获取结果失败: {data.get('errorDescription')}")
                    return None
                
                if data.get('status') == 'ready':
                    return data.get('solution', {}).get('token')
                
            return None

    async def _solve_local(self, url: str, sitekey: str) -> Optional[str]:
        """使用本地/远程 Solver 接口求解"""
        async with httpx.AsyncClient(timeout=120) as client:
            # 创建并获取结果（根据 grok/api_solver.py 的逻辑，这是一个阻塞调用或分步调用）
            # 这里的逻辑对应 grok/g/turnstile_service.py
            
            # Step 1: 创建任务
            task_url = f"{self.solver_url}/turnstile?url={url}&sitekey={sitekey}"
            resp = await client.get(task_url)
            data = resp.json()
            task_id = data.get('taskId')
            
            if not task_id:
                logger.error("[Turnstile] Solver 未返回 taskId")
                return None
            
            # Step 2: 轮询结果
            for _ in range(60):
                await asyncio.sleep(2)
                result_url = f"{self.solver_url}/result?id={task_id}"
                resp = await client.get(result_url)
                data = resp.json()
                
                solution = data.get('solution', {})
                token = solution.get('token')
                
                if token:
                    if token == "CAPTCHA_FAIL":
                        logger.error("[Turnstile] Solver 返回验证失败")
                        return None
                    return token
            
            return None

turnstile_manager = TurnstileManager()
