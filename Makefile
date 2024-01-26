.PHONY: build-web hooks

build-web:
	cd viz/web/frontend && npm install

hooks:
	pre-commit install --overwrite --install-hooks --hook-type pre-commit --hook-type post-checkout --hook-type pre-push
	git checkout