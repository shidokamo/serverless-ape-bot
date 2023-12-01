include .env
export

install:
	pipenv install

run:
	pipenv run python3 main.py

requirements:
	pipenv requirements --exclude-markers > requirements.txt
deploy:requirements
	gcloud functions deploy ${NAME} \
		--gen2 \
		--region=${REGION} \
		--runtime=python310 \
		--source=${PWD} \
		--entry-point=run \
		--trigger-http \
		--set-env-vars API_KEY=${API_KEY} \
		--set-env-vars API_SECRET=${API_SECRET} \
		--set-env-vars API_PASS=${API_PASS} \
		--set-env-vars LEVERAGE_INIT=${LEVERAGE_INIT} \
		--set-env-vars LEVERAGE_MIN=${LEVERAGE_MIN} \
		--set-env-vars LEVERAGE_DECAY=${LEVERAGE_DECAY} \
		--set-env-vars LEVERAGE_REF_PRICE=${LEVERAGE_REF_PRICE} \
		--set-env-vars BASE=${BASE} \
		--set-env-vars QUOTE=${QUOTE} \
		--set-env-vars ORDER_SIZE=${ORDER_SIZE} \
		--set-env-vars MAX_INIT_PRICE=${MAX_INIT_PRICE} \
		--set-env-vars NO_ORDER_LIMIT=${NO_ORDER_LIMIT} \
		--set-env-vars TAKE_PROFIT_LIMIT_PRICE=${TAKE_PROFIT_LIMIT_PRICE} \
		--set-env-vars PROD=TRUE \

log:
	gcloud functions logs read ${NAME} --gen2

job:
	gcloud scheduler jobs create http ${NAME} \
		--schedule="every 1 minutes" \
		--uri=${URI} \
		--oidc-service-account-email=${SCHEDULER_SERVICE_ACCOUNT}

