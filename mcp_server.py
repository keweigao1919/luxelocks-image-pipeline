#!/usr/bin/env python3
"""
LuxeLocks Hub MCP Server
通过 MCP 协议让 Claude 直接操作订单系统
"""

import json
import sys
import httpx

HUB_URL = "http://localhost:8001"


async def handle_request(method: str, params: dict = None) -> dict:
    """转发请求到 LuxeLocks Hub API"""
    params = params or {}

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "get_orders",
                    "description": "查询订单列表。可按状态筛选、搜索客户名/订单号/运单号。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "订单状态: pending(待处理), paid(已付款), shipped(已发货), cancelled(已取消), 不填则全部"
                            },
                            "search": {
                                "type": "string",
                                "description": "搜索关键词，匹配订单号/客户名/运单号"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回数量，默认20",
                                "default": 20
                            }
                        }
                    }
                },
                {
                    "name": "get_inventory",
                    "description": "查询产品库存。可按SKU搜索。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "sku": {
                                "type": "string",
                                "description": "产品SKU，支持模糊搜索，不填则返回低库存产品"
                            }
                        }
                    }
                },
                {
                    "name": "get_stats",
                    "description": "获取今日运营汇总：今日订单数、待处理数、今日发货数、低库存告警数。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "sync_orders",
                    "description": "手动触发 Shopify 订单同步。拉取最新50个订单。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_sync_log",
                    "description": "查看最近的数据同步日志。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "返回条数，默认20",
                                "default": 20
                            }
                        }
                    }
                },
                {
                    "name": "search_orders",
                    "description": "快速搜索订单：搜订单号、运单号、客户名均可。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "add_tracking",
                    "description": "给订单添加物流单号，标记为已发货。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "订单ID或订单号"
                            },
                            "tracking_number": {
                                "type": "string",
                                "description": "物流运单号"
                            },
                            "tracking_company": {
                                "type": "string",
                                "description": "物流公司，默认云途物流",
                                "default": "云途物流"
                            }
                        },
                        "required": ["order_id", "tracking_number"]
                    }
                },
                {
                    "name": "lookup_tracking",
                    "description": "根据运单号查询物流轨迹和对应订单。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "tracking_number": {
                                "type": "string",
                                "description": "物流运单号"
                            }
                        },
                        "required": ["tracking_number"]
                    }
                }
            ]
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        async with httpx.AsyncClient() as client:
            if tool_name == "get_orders":
                query_params = {}
                if args.get("status"):
                    query_params["status"] = args["status"]
                if args.get("search"):
                    query_params["search"] = args["search"]
                if args.get("limit"):
                    query_params["limit"] = args["limit"]
                resp = await client.get(f"{HUB_URL}/api/mcp/orders", params=query_params)
                return {
                    "content": [{"type": "text", "text": json.dumps(resp.json(), ensure_ascii=False, indent=2)}]
                }

            elif tool_name == "get_inventory":
                query_params = {}
                if args.get("sku"):
                    query_params["sku"] = args["sku"]
                resp = await client.get(f"{HUB_URL}/api/mcp/inventory", params=query_params)
                return {
                    "content": [{"type": "text", "text": json.dumps(resp.json(), ensure_ascii=False, indent=2)}]
                }

            elif tool_name == "get_stats":
                resp = await client.get(f"{HUB_URL}/api/mcp/stats")
                return {
                    "content": [{"type": "text", "text": json.dumps(resp.json(), ensure_ascii=False, indent=2)}]
                }

            elif tool_name == "sync_orders":
                resp = await client.post(f"{HUB_URL}/api/sync/orders")
                return {
                    "content": [{"type": "text", "text": json.dumps(resp.json(), ensure_ascii=False, indent=2)}]
                }

            elif tool_name == "get_sync_log":
                query_params = {"limit": args.get("limit", 20)}
                resp = await client.get(f"{HUB_URL}/api/mcp/sync_log", params=query_params)
                return {
                    "content": [{"type": "text", "text": json.dumps(resp.json(), ensure_ascii=False, indent=2)}]
                }

            elif tool_name == "search_orders":
                resp = await client.get(f"{HUB_URL}/api/search", params={"q": args["query"]})
                results = resp.json().get("results", [])
                if not results:
                    return {"content": [{"type": "text", "text": "没有找到匹配的订单"}]}
                return {
                    "content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False, indent=2)}]
                }

            elif tool_name == "add_tracking":
                resp = await client.post(f"{HUB_URL}/api/tracking/add", json={
                    "order_id": args["order_id"],
                    "tracking_number": args["tracking_number"],
                    "tracking_company": args.get("tracking_company", "云途物流")
                })
                return {
                    "content": [{"type": "text", "text": json.dumps(resp.json(), ensure_ascii=False, indent=2)}]
                }

            elif tool_name == "lookup_tracking":
                resp = await client.get(f"{HUB_URL}/api/tracking/lookup/{args['tracking_number']}")
                return {
                    "content": [{"type": "text", "text": json.dumps(resp.json(), ensure_ascii=False, indent=2)}]
                }

            else:
                return {"content": [{"type": "text", "text": f"未知工具: {tool_name}"}]}

    return {}


async def main():
    """MCP stdio 主循环"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())
            method = request.get("method", "")
            req_id = request.get("id")

            result = await handle_request(method, request.get("params", {}))

            response = {"jsonrpc": "2.0", "id": req_id}
            response.update(result)
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_resp = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in dir() else None,
                "error": {"code": -1, "message": str(e)}
            }
            sys.stdout.write(json.dumps(error_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
