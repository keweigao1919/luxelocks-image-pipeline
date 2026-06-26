# LuxeLocks Hub - 唯一开发指南

> **⚠️ 这是 Claude Code + Claude + Codex 三方共用的唯一权威文档。任何 AI 开始工作前必须先读此文件 + WORKING.md。**

---

## 技术栈
Python 3.12 + FastAPI + Uvicorn + SQLite (`luxelocks.db`) + Jinja2
外部API: Shopify REST 2025-04 / 领星 OMS / 华威尔 TMS
邮件: QQ SMTP (gkway@qq.com)
UNC媒体路径: `\\huawei\Users\HUAWEI\Pictures\产品`
启动: `python -m uvicorn app:app --host 0.0.0.0 --port 8001` → http://localhost:8001
入口: `app.py` (~3000行)

---

## 数据库完整结构

### orders (5条)
```
id PK, platform, platform_order_id, order_number(LL-1009), customer_name, customer_email,
total_price, currency(USD), status(pending/paid/shipped/cancelled/refunded),
shipping_address(JSON), tracking_number, tracking_company, line_items(JSON:[{sku,title,qty,price}]),
shipping_type(海外仓发货/国内直发,订单同步时固化), raw_data, created_at, updated_at
```
索引: idx_orders_platform, idx_orders_status, idx_orders_created

### products (90条)
```
id PK, platform(shopify), platform_product_id, sku(SWLC2068-9BL18),
title, variant_title, price, inventory_quantity(同步更新), image_url,
product_status(active/draft/archived), variant_id(Shopify变体ID), inventory_item_id(库存项ID),
oms_available_qty, oms_transit_qty, created_at, updated_at
```
索引: idx_products_sku

### procurement_resources (89条)
```
id PK, simple_sku(UNIQUE, 如2068-9), supplier, seller_id(关联suppliers),
cost, estimated_delivery, purchase_link, contact_name, wechat, notes, image_url,
created_at, updated_at
```
索引: idx_procurement_sku_uq

### suppliers (2条)
```
id PK, name, seller_id(关联匹配键), purchase_link, contact_name, wechat,
created_at, updated_at
```

### warehouse_inventory (60条)
```
id PK, reference_code(GD-2068-09), warehouse_name(CrossBorder/NewProducts/LuxeLocks/VelouraHair),
available_inventory, in_transit_total, ...(其他字段)
```
索引: idx_warehouse_name, idx_warehouse_ref

### sku_mapping (3条)
```
id PK, shopify_simple_sku UNIQUE, cross_border_simple_sku,
luxelocks_simple_sku, velourahair_simple_sku
```

### reminders (1条)
```
id PK, title, content, remind_date(YYYY-MM-DD), email, sent(0/1),
repeat_type(''/monthly/weekly), repeat_day
```

### tiktok_skus
```
id PK, sku UNIQUE, product_name, color, length, price, product_cost, shipping_fee,
platform_fee_rate, ad_cost, return_rate, refund_loss, stock, daily_sales,
lead_time_days, safety_stock, status(testing/main/restock/clear/paused), notes,
created_at, updated_at
```

### tiktok_videos
```
id PK, account_name, sku, tiktok_video_id, tiktok_product_id, product_name,
creator_id, publish_date, video_angle, hook, selling_points, display_order,
voiceover, cover_text, caption, hashtags, posted(0/1), views, likes_count,
comments_count, shares_count, product_impressions, product_clicks, orders,
gmv, video_ctr, completion_rate, gpm, comments, platform_diagnosis,
diagnosis, repeat_action, source_file, created_at, updated_at
```

### tiktok_video_performance
```
id PK, import_key UNIQUE(video_id|tiktok_product_id), creator_nickname, creator_id,
video_info, video_id, publish_time, product_name, tiktok_product_id,
sku, simple_sku, vv, likes_count, comments_count, shares_count,
new_followers_count, product_redirects, product_impressions, product_clicks,
unique_customers, attributed_sku_orders, video_sku_orders, indirect_sku_orders,
attributed_units, product_units, indirect_units, attributed_gmv, video_gmv,
indirect_gmv, gpm, video_ctr, redirect_rate, completion_rate, ctor_sku_orders,
platform_diagnosis, local_diagnosis, repeat_action, source_file, imported_at, updated_at
```

### tiktok_sku_mapping
```
id PK, tiktok_product_id UNIQUE, sku, simple_sku, price, product_cost,
shipping_fee, platform_fee_rate, ad_cost, refund_loss, return_rate, notes,
created_at, updated_at
```

### 其他表
sync_log(128条), headhaul_orders(0条), important_matters(3条), inventory_log(0条)

---

## 核心函数

### simplify_sku(sku) → str
```python
match = re.search(r'(\d+-\d+)', sku)
return match.group(1) if match else sku
# SWLC2068-9BL18 → 2068-9
```

### get_db()
```python
conn = sqlite3.connect(str(DB_PATH), timeout=30)
conn.row_factory = sqlite3.Row  # row['col']访问
conn.execute("PRAGMA busy_timeout=30000")
return conn
# 必须 finally: conn.close()
```

### ShopifyConnector实例 (shopify)
- get_products(limit) / get_orders(limit,status) / get(path)
- set_inventory(inventory_item_id, location_id, available, variant_id) — 自动开启跟踪+连接
- untrack_variant(variant_id) — 取消跟踪继续卖
- refresh_token() — 24h过期，启动时自动刷新

### OMS
```python
await oms_call("/v1/integratedInventory/pageOpen", {"page":1,"pageSize":50})
await oms_call("/v1/outboundOrder/pageList", {...})
```

### split_tiktok_product(raw_product) → (product_name, product_id)
```python
def split_tiktok_product(raw_product):
    text = str(raw_product or "").strip()
    match = re.search(r"\((\d{8,})\)\s*$", text)
    if not match:
        return text, ""
    return text[:match.start()].strip(), match.group(1)
# "商品名(1732277674835415824)" → ("商品名", "1732277674835415824")
```

### 模板
```python
render_html("模板.html", request, key=val)
# 用 {% for %} 构建 JS 数组，禁止内联 {{ r|tojson|safe }} 在 HTML 属性
# 表格交互统一走 partial=1 局部刷新，不整页跳转
```

### ⚠️ 运维提醒
**改完 app.py 必须重启 uvicorn 服务，否则跑旧代码。**
出现"改了没效果"先确认已重启，不要急着怀疑逻辑/重写代码。

---

## 关键数据流

### 库存匹配链
```
SKU: SWLC2068-9BL18 → simplify("2068-9")
→ sku_mapping.shopify_simple="2068-9" → cross_border_simple="2068-09"
→ warehouse.ref="GD-2068-09" → simplify("2068-09")
→ 以简化SKU为key匹配!
```

### 运输类型(订单同步时固化)
```
line_items → simplify(sku) → sku_mapping → warehouse
→ available>0 → "海外仓发货", 否则 "国内直发"
```

### 库存同步到Shopify (📤按钮)
```
cross_inv{simplified_sku: total_avail} ← warehouse_inventory汇总
→ products遍历: avail>0 → track+set / avail=0且OMS管理 → untrack / 其他 → skip
→ 本地 inventory_quantity 同步更新
```

---

## 路由总览

| 路由 | 页面 | 模板 |
|------|------|------|
| `/` | 首页 | dashboard.html |
| `/orders` | 订单 | orders.html |
| `/order/{id}` | 订单详情 | order_detail.html |
| `/products` | 产品 | products.html |
| `/procurement` | 采购池 | procurement.html |
| `/suppliers` | 供应商 | suppliers.html |
| `/media` | 素材 | media.html |
| `/tiktok` | TikTok运营 | tiktok.html |
| `/tiktok-videos` | TikTok视频表现导入表 | tiktok_videos.html |
| `/tiktok-sku` | TikTok商品ID-SKU映射表 | tiktok_sku.html |
| `/reminders` | 提醒 | reminders.html |
| `/headhaul` | 头程 | headhaul.html |
| `/sku-mapping` | SKU映射 | sku_mapping.html |
| `/inventory/*` | 库存 | inventory_*.html |

base.html = 侧边栏+标签页+Toast+syncOrders/syncOMSTracking/lookupTracking

---

## 开发约定

1. **DB**: conn=get_db() → row['col'] → finally conn.close()
2. **前端**: Jinja2+原生JS，JSON给JS用for循环构建数组
3. **按钮**: 所有按钮必须有 title 属性
4. **编码**: GBK→UTF-8，路径用 fsencode/fsdecode
5. **性能**: 媒体树缓存5min，图片代理缓存 .img_cache/
6. **新功能**: ALTER TABLE → 路由 → 模板
7. **同步API**: 可能超时，后台用 asyncio.create_task()

---

## 协作规则（Claude Code + Claude + Codex 三方）

### 开始前（必须，否则撞车）
1. **读 WORKING.md** → 看有没有人在干活。有人就等或做别的，没人就写上行查入
2. **读本文件末尾变更记录** → 了解最新改动
3. **git pull** → 拉最新代码
4. **git add WORKING.md && git commit -m "checkin: <AI名> working on <任务>"**

### 完成时（必须，否则别人不知道）
1. **更新本文件末尾的 [变更记录]** — 格式: `| 日期 | AI名 | 改了什么, 涉及文件 |`
2. **清除 WORKING.md 中自己的行**
3. **git add -A && git commit -m "<AI名>: <改动摘要>"**
4. **git push**（如果配置了远程仓库）

### 禁止
- 同时编辑同一个文件（通过 WORKING.md 避免）
- 改了代码不更新变更记录
- 改了代码不 git commit

---

## 变更记录

| 日期 | AI | 改动内容 |
|------|-----|---------|
| 2026-06-26 | Codex | 脚本工厂改为视频ID驱动复拍模板：app.py 新增按 TikTok Videos 视频ID预查询/生成接口、视频来源SKU解析、复拍模板脚本生成和价格为0时避免输出$0；templates/tiktok.html 新增视频ID输入、自动带出当前SKU/简化SKU/商品ID、生成逻辑/视频来源区，并按来源视频生成卖点角度、口播、封面和发布文案 |
| 2026-06-26 | Codex | 修复 TikTok 排序细节：app.py 补齐 TikTok Videos表 SELECT 指标字段并用白名单排序表达式，互动改按点赞+评论+分享总和排序，Wig Ops 视频复盘 CTR 改按点击/播放实时排序；templates/_tiktok_videos_review.html + templates/tiktok.html 改为行内数据编辑/按ID删除，避免 AJAX 排序后编辑错行，并修复 #videos 下 partial=1 追加位置 |
| 2026-06-25 | Codex | 调整 TikTok Wig Ops 的 SKU利润/补货表头：templates/tiktok.html 将卡片内“＋ 新增”按钮改为 SKU / 简化SKU / 商品ID 搜索框，支持实时过滤当前利润补货表内SKU并显示匹配数量 |
| 2026-06-25 | Codex | 调整 TikTok Wig Ops 的 SKU利润/补货表排期选择：templates/tiktok.html 中 SKU 勾选框默认不再选中，必须手动勾选后才参与视频排期生成 |
| 2026-06-25 | Codex | 优化 TikTok Wig Ops 与 TikTok SKUs表联动：app.py 新增合并SKU候选/简化SKU/商品ID查找逻辑，TikTok SKUs映射保存时自动同步 tiktok_skus；templates/tiktok.html 脚本工厂支持输入完整SKU、简化SKU或TikTok商品ID并显示来源，SKU利润/补货表显示来源标签 |
| 2026-06-26 | Claude Code | 收尾清理: 导入改用AJAX局部刷新不再整页跳转; 删除products.html搜索Date.now()时间戳; CLAUDE.md补登记split_tiktok_product+partial=1约定+运维提醒(改py必重启) |
| 2026-06-26 | Claude Code | **排序/翻页AJAX化去弹顶**: Page A新增_tiktok_videos_table.html局部模板+JS事件委托拦截+replaceState; Page B新增_tiktok_videos_review.html+JS delegate; 路由partial=1返回表格片段; 渐进增强(无JS仍可用) |
| 2026-06-26 | Claude Code | Wig Ops视频复盘加表头排序: tiktok路由加sort/order+白名单(views/product_clicks/orders/video_ctr); tiktok.html宏生成排序链接+箭头; 整表排序后分页 |
| 2026-06-26 | Claude Code | TikTok Videos表加表头排序: 扩展白名单(VV/互动/曝光点击/订单/件数/GMV); Jinja2 sort_link宏+箭头; 翻页保留sort/order; 全列数值型无需剥格式 |
| 2026-06-26 | Claude Code | **映射口径切simple_sku**: 导入逻辑取mapping.simple_sku不再拼TT-; 已映射=simple_sku非空,未映射=空; 回填524条(464 mapped/60 unmapped); 统计/筛选/模板全切换; 验证2074-1替代TT-2074-1; **新口径: SKU以simple_sku为准,匹配键tiktok_product_id(TEXT)** |
| 2026-06-26 | Claude Code | TikTok SKUs表加搜索: app.py路由加q参数(参数化LIKE,匹配sku/simple_sku/tiktok_product_id三列全部TEXT); tiktok_sku.html加搜索框+清除链接+结果计数; 验证全ID/部分ID/SKU片段均命中 |
| 2026-06-26 | Claude Code | 列重排: tiktok_videos.html将tiktok_product_id从商品列移除,新增独立商品ID列(SKU后),等宽字体显示19位数字; 未改DB和抽取逻辑 |
| 2026-06-26 | Claude Code | 新增product_id字段: ALTER TABLE tiktok_video_performance加product_id TEXT; 回填524条(从现有tiktok_product_id复制,product_name无ID可抽); upsert_tiktok_video_performance和列表SELECT加入product_id; 全量19位数字0 NULL |
| 2026-06-25 | Claude Code | 修复TikTok Videos页面卡顿: app.py加分页(page/LIMIT50)改SELECT精简16列(原40列)+排序白名单; tiktok_videos.html去location.reload改window.location.href+添加上一页/下一页导航; 诊断确认无iframe嵌入,524条分11页 |
| 2026-06-25 | Codex | 新增 TikTok Videos 表导入页：app.py 添加 tiktok_video_performance 表、扩展 tiktok_videos 指标字段、完善 tiktok_sku_mapping 映射表/API、支持导入 TikTok Video Performance List xlsx 并同步到 Wig Ops 视频复盘；base.html 新增 /tiktok-videos 与 /tiktok-sku 入口；新增 tiktok_videos.html 与完善 tiktok_sku.html |
| 2026-06-25 | Codex | 补全 TikTok Wig Ops 页面 hover 指导信息：templates/tiktok.html 为标题、统计卡、表头、数据行、脚本工厂、排期、视频复盘和弹窗字段增加 title，说明数据来源/计算逻辑/操作方法 |
| 2026-06-25 | Codex | 新增 TikTok Wig Ops 中控模块：app.py 添加 tiktok_skus/tiktok_videos 表、利润/补货计算、脚本生成、7天排期、视频复盘API；templates/base.html 增加入口；新增 templates/tiktok.html 页面 |
| 2026-06-25 | Codex | 补齐三方入口文档：memory/MEMORY.md 与 .cursorrules 均要求先读 WORKING.md + CLAUDE.md，避免 Claude/Claude Code/Codex 漏看实时看板 |
| 2026-06-25 | Claude Code | 三方协作基建: 创建 WORKING.md 活动看板, 更新 CLAUDE.md 协作规则支持 Claude+Codex+ClaudeCode 三方, 更新 AGENTS.md 指向 WORKING.md, git init 就绪 |
| 2026-06-25 | Codex | 补齐协作基建：新增 memory/MEMORY.md 指向 CLAUDE.md，新增 .gitignore 避免提交 venv/日志/数据库，并准备初始化 git 提交流程 |
| 2025-06-19 | Claude Code | 初始创建本文件，统一开发指南 |
