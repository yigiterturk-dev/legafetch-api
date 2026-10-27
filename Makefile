.PHONY: gateway-build gateway-test gateway-lint gateway-audit verify

gateway-build:
	cd gateway && npm run build

gateway-test:
	cd gateway && npm test

gateway-lint:
	cd gateway && npm run lint

gateway-audit:
	cd gateway && npm audit --omit=dev --audit-level=high

verify: gateway-build gateway-test gateway-lint gateway-audit
	@echo "LegaFetch verification passed"
