import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# 确保导入路径正确
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from app.services.grok.turnstile import TurnstileManager

async def test_turnstile_manager():
    print("开始测试 TurnstileManager...")
    manager = TurnstileManager()
    
    # 模拟成功的求解返回
    manager._solve_local = AsyncMock(return_value="mock_token_12345")
    manager.solver_url = "http://localhost:5072"
    
    token = await manager.solve()
    print(f"Token: {token}")
    assert token == "mock_token_12345"
    print("TurnstileManager 测试成功！")

if __name__ == "__main__":
    asyncio.run(test_turnstile_manager())
