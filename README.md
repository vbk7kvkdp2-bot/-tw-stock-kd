# 台股每日 KD 追蹤網頁儀表板

## 功能
- 預設追蹤：006208、00900、00929、00941、2884、2887、2892、4118
- 每次開啟或按「重新抓取最新資料」時取得日線行情
- 計算 KD(9,3,3)
- 顯示黃金交叉、死亡交叉、K/D 低於 20 或高於 80
- 顯示個股 KD 圖與最近 20 個交易日資料
- 可下載每日總覽 CSV

## 需求
安裝 Python 3.10 或更新版本，並確保電腦可連上網路。

## 安裝與啟動

### Windows
1. 將 ZIP 解壓縮。
2. 在解壓後的資料夾空白處開啟終端機／PowerShell。
3. 執行：
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. 瀏覽器開啟 `http://localhost:8501`。

若 PowerShell 不允許啟用虛擬環境，可略過啟用步驟，改用：
`.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
及
`.\.venv\Scripts\python.exe -m streamlit run app.py`

### macOS
在終端機進入此資料夾，執行：
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```
瀏覽器開啟 `http://localhost:8501`。

## 每天怎麼看
1. 開啟電腦並啟動程式：`streamlit run app.py`。
2. 瀏覽器進入 `http://localhost:8501`。
3. 按「重新抓取最新資料」取得新資料；行情通常在交易日收盤後更新，實際以資料源為準。
4. 查看「庫存 KD 總覽」；需要時選擇個股查看 KD 走勢。
5. 可按「下載今日總覽 CSV」保存當日結果。
6. 用完後在終端機按 `Ctrl+C` 停止程式。

## 行情來源與限制
- 使用 Yahoo Finance 的日線歷史行情，透過 `yfinance` 套件讀取。
- 上市代碼會嘗試 `代號.TW`，上櫃代碼會嘗試 `代號.TWO`。
- 這不是證交所／櫃買中心官方交易終端，資料可能延遲、缺漏、修正或因代號變更而無法取得。
- 程式不會在背景自動推播；需要每天打開網頁或按重新抓取。若要全天候可從手機查看，需部署至雲端服務；若希望自動寄送提醒，還需另加排程與通知服務。
- 免費雲端主機可能休眠或有資源限制。
- KD 計算採用常見的遞迴平滑法；不同平台的初始化方法、還原權息調整設定可能造成數值略有差異。
- 這是技術分析參考，不構成投資建議。

## 常見問題
- **某檔沒有資料：**檢查代號是否仍有效；程式會依序試 `.TW` 和 `.TWO`。代號變更或資料源暫時故障時，可能需要更新代碼。
- **資料日期不是今天：**非交易日、收盤資料尚未更新或來源延遲時，日期會停留在最近可取得的交易日。
- **想每天自動更新：**目前是手動開啟／重新抓取。可將程式部署到雲端，但網頁本身不保證背景排程；另需設定定時工作。
