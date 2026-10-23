# rag-api image（Hono，node dist/index.js）。
#
# 同一份 Dockerfile 供兩個用途：
#   - docker-compose 本機開發（PORT 由 compose 覆寫為 8002）
#   - .github/workflows/deploy-rag-api.yml 建置 linux/arm64 image 推到 ECR vocus-warehouse-rag
#     （vocus-stg 的 Karpenter NodePool 是 Graviton）
#
# 釘住的外部輸入（改版時一併更新註解日期）：
#   - 基底：node:22-slim 的多架構 index digest，2026-10-23 以
#     `docker buildx imagetools inspect node:22-slim` 取得（Debian bookworm，內含 linux/arm64 與 amd64）
#   - RDS CA bundle global-bundle.pem 的 sha256：與 vocus-warehouse Dockerfile 相同（2026-10-15 計算，
#     2026-10-23 重新下載比對一致）。bundle 輪替時兩邊一起更新。
#
# 不含 curl、不含任何 secret；執行期設定一律由環境變數注入。
# DB 憑證由 K8s Secret vocus-warehouse-db-rag 掛載，env VW_DB_SECRET_FILE_RAG 指向（見 src/store/pg-client.ts）；
# TLS 一律 verify-full，CA 用本 image 內的 /etc/ssl/rds/global-bundle.pem（PGSSLROOTCERT）。
ARG NODE_IMAGE=node:22-slim@sha256:de170b39439eb0e5a3444ad7d60b015614a381e10fecae2e30ec9e735122f38d

# Stage 0: RDS CA bundle（node fetch 下載，sha256sum -c 驗證後才進 runtime image）
FROM ${NODE_IMAGE} AS rds-ca

ARG RDS_BUNDLE_URL=https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
ARG RDS_BUNDLE_SHA256=90a6f1a7978a1b1b096dca6c57511ca48d3b8cf052f8e704baf358f34ea2f21b

RUN node -e "fetch(process.argv[1]).then(async (r) => { if (!r.ok) throw new Error('HTTP ' + r.status); require('node:fs').writeFileSync('/tmp/global-bundle.pem', Buffer.from(await r.arrayBuffer())); })" "${RDS_BUNDLE_URL}" \
    && echo "${RDS_BUNDLE_SHA256}  /tmp/global-bundle.pem" | sha256sum -c -

# Stage 1: 全部依賴 + build
FROM ${NODE_IMAGE} AS builder

# pnpm 版本由 package.json 的 packageManager 欄位決定
RUN corepack enable pnpm

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY tsconfig.json tsup.config.ts ./
COPY src/ ./src/

RUN pnpm build

# Stage 2: 只含 production 依賴（runner 不帶 pnpm／devDependencies）
FROM ${NODE_IMAGE} AS prod-deps

RUN corepack enable pnpm

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --prod

# Stage 3: runtime
FROM ${NODE_IMAGE} AS runner

ARG APP_UID=10001

# 預設 8080；docker-compose 會以 PORT=8002 覆寫
ENV NODE_ENV=production \
    PORT=8080 \
    PGSSLROOTCERT=/etc/ssl/rds/global-bundle.pem

# 非 root。USER 用數字 uid，kubernetes runAsNonRoot 才能在不查 /etc/passwd 的情況下驗證
RUN groupadd --gid "${APP_UID}" app \
    && useradd --uid "${APP_UID}" --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# package.json 必須在：決定 dist/index.js 以 ESM 載入（"type": "module"）
COPY --chown=${APP_UID}:${APP_UID} package.json ./
COPY --from=prod-deps --chown=${APP_UID}:${APP_UID} /app/node_modules ./node_modules
COPY --from=builder --chown=${APP_UID}:${APP_UID} /app/dist ./dist
COPY --from=rds-ca --chmod=0644 /tmp/global-bundle.pem /etc/ssl/rds/global-bundle.pem
# BuildKit 的 COPY --chmod 會把 COPY 順手建出的目錄（/etc/ssl、/etc/ssl/rds）也設成 0644，非 root 無法
# 進入目錄，Node 啟動讀 openssl.cnf 時 EACCES 直接 crash（2026-10-23 vocus-stg 實測）。目錄補回 0755。
RUN chmod 0755 /etc/ssl /etc/ssl/rds

USER ${APP_UID}:${APP_UID}

EXPOSE 8080

# /health 不需 auth、不查資料庫。start-period 預留 cold start 預載 QA store 的時間
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:'+(process.env.PORT||8080)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

CMD ["node", "dist/index.js"]
