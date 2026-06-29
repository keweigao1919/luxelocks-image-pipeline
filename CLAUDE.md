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
8. **JS事件绑定**: 部分交互靠 addEventListener 隐式绑定(如#skuProfitSearch)，HTML属性看不到。改模板元素前先 grep 该 id 在JS的引用，确认无隐式事件依赖再动。

---

## 协作规则（Claude Code + Claude + Codex 三方）

### Codex 两种工作模式

用户可以随时用“模式1”或“模式2”切换 Codex 的工作方式。切换以后，Codex 必须在回复开头确认当前模式。

#### 模式1：安排 Claude Code
适用场景：用户说“模式1”“安排 Claude Code”“领导模式”“出工单”“让 Claude Code 体检/执行”“先诊断不要改”。

Codex 角色：技术负责人 / 调度者，不直接改业务代码，主要负责拆任务、定边界、写工单、排优先级、做交接。

模式1必须做到：
1. 先读 `WORKING.md`、本文件变更记录、`git log --oneline -5`。
2. 判断任务是否适合交给 Claude Code / Claude / Codex 自己。
3. 输出清晰工单，格式包含：目标、范围、禁止事项、执行步骤、验证方法、输出格式。
4. 如果用户要求持久交接，可以把任务写入 `WORKING.md` 的“排队中”或本文件“已知待办”，并提交文档变更。
5. 默认不改 `app.py`、模板、数据库结构等业务代码，除非用户明确说“模式1也可以帮我落文档/排队”。
6. 工单要避免撞文件，明确“谁改哪些文件、谁不能碰哪些文件”。

模式1输出示例：
```
当前模式：模式1 安排 Claude Code
给 Claude Code 的工单：
- 目标：
- 范围：
- 禁止：
- 步骤：
- 验证：
- 输出：
```

#### 模式2：自己干
适用场景：用户说“模式2”“你直接做”“直接修复执行”“自己干”“改代码”“实现”。

Codex 角色：执行者，直接读代码、改代码、测试、更新变更记录、提交。

模式2必须做到：
1. 按三方协作流程先 check-in。
2. 只改与任务直接相关的文件，避免碰其他 AI 正在改的文件。
3. 改完必须验证：至少语法检查 / 页面渲染 / 接口或浏览器检查，按风险选择。
4. 更新本文件变更记录。
5. 清除 `WORKING.md` 中自己的行。
6. git commit，并在最终回复里通知 Claude / Claude Code 读取最新变更。

默认规则：如果用户没有指定模式，但说“检查一下、深入思考、给建议、安排 Claude Code”，默认模式1；如果用户说“你直接修复执行、完成、改好”，默认模式2。

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

## 已知待办 (低优先,择期)
- [ ] tiktok.html: 5处 location.reload() — Wig Ops SKU/视频增删改后整页弹顶,改AJAX局部刷新
- [ ] tiktok_sku.html: 2处 location.reload() — SKU映射增删后弹顶,改AJAX
- [ ] suppliers.html: 2处 location.reload() — 供应商增删后弹顶
- [ ] reminders.html: 2处 location.reload() — 提醒增删后弹顶
- [ ] tiktok_sku_mapping: simple_sku 有2个重复值(3157-2,3172-3),多商品ID指向同SKU,属正常业务

---

## 变更记录

| 日期 | AI | 改动内容 |
|------|-----|---------|
| 2026-06-28 | Claude Code | 订单页UI优化: status_badge宏覆盖6值+refunded红色; tab只选中亮色未选中灰; 表头#f5f6fa+行hover; 金额$+tabular-nums; 运单mono+点击复制; 空值—; DB状态全英文但显示中文 |
| 2026-06-28 | Claude Code | 首页看板优化: KPI4列横排+已发货/总计可点击; fmttime过滤器; 低库存口径统一为active+inventory=0; 低库存提醒<10档; DefaultTitle清洗 |
| 2026-06-28 | Claude Code | Wig Ops UI: 产品名列-webkit-line-clamp截断+行hover+tabular-nums; #ttOps作用域; 标红行brightness保护 |
| 2026-06-28 | Claude Code | TikTok Videos UI试点: Inter字体+tabular-nums数字对齐+tbody tr:hover淡灰; #tvPage作用域隔离; 标红行hover保护 |
| 2026-06-28 | Claude Code | TikTok Videos优化: 未映射行SKU列加去映射按钮(跳转/tiktok-sku?q=商品ID); 视频ID做成TikTok外链; 空视频文案显示无文案; 排序箭头已存在免补 |
| 2026-06-28 | Claude Code | 库存预警: 在售+Shopify库存=0标红; 总计行加title标注列名; 清空按钮改输入确认加固; 总计加在售缺货SKU计数 |
| 2026-06-28 | Claude Code | 产品页展示优化: 品名单行截断+title hover; 操作列sticky right; 规格DefaultTitle显示-; 同步修复断裂a标签bug |
| 2026-06-28 | Claude Code | 新增/sync-logs只读同步日志查看页: sync_log表已存在136条,复用分页+partial=1; 三种同步已内置写日志无需埋点; 侧栏加同步日志链接; action映射中文 |
| 2026-06-26 | Claude Code | Wig Ops修复: quickScript加滚动高亮toast; skuProfitSearch显式oninput; 复盘表sticky表头; 成本未填警告; CLAUDE.md加JS事件绑定约定 |
| 2026-06-26 | Claude Code | 修4项低风险bug: 侧栏重要事项/matters改/reminders; tiktok_videos表格overflow-x:auto; order_detail补退款badge; applyFilter搜索保留sort/order/page |
| 2026-06-26 | Claude Code | Page A loadTable加reqId竞态保护+.catch容错; 清理WORKING.md旧任务残留 |
| 2026-06-26 | Codex | 新增 Codex 两种工作模式协作规则 |
| 2026-06-26 | Codex | 拆分 TikTok Wig Ops 排期任务与视频复盘：app.py 新增 tiktok_video_tasks 待发布任务表、旧待发布纯计划迁移、排期保存改写任务表、任务已发布/跳过/删除接口，复盘查询过滤未发布纯计划；templates/tiktok.html 新增“待发布排期任务”卡片，生成并保存改为保存任务，发布后再“已发布→复盘” |
| 2026-06-26 | Claude Code | 体检修复-加JOIN索引: idx_tiktok_sku_map_pid + idx_tvp_pid; init_db自动建 |
| 2026-06-26 | Claude Code | 体检修复-Page B loadVideoReview加容错: .catch失败提示+恢复旧内容+reqId竞态保护 |
| 2026-06-26 | Codex | 脚本工厂改为视频ID驱动复拍模板 |
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
