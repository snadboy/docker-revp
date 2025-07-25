# [3.6.0](https://github.com/snadboy/docker-revp/compare/v3.5.0...v3.6.0) (2025-07-25)


### Bug Fixes

* correct SSH key path in hosts.yml configuration ([4c4a049](https://github.com/snadboy/docker-revp/commit/4c4a049040aab2ce665d840b78aebbde823524fd))


### Features

* integrate SSH Docker Client library ([e13ca29](https://github.com/snadboy/docker-revp/commit/e13ca299deb4f09d90694180b8b480ada38dd088))
* publish and migrate to snadboy-ssh-docker PyPI package ([d649ef4](https://github.com/snadboy/docker-revp/commit/d649ef41f4b68811dfbcc7048645430fd132822b))

# [3.5.0](https://github.com/snadboy/docker-revp/compare/v3.4.0...v3.5.0) (2025-07-23)


### Features

* enhance hosts dashboard with improved UX and remove legacy DOCKER_HOSTS support ([7f27432](https://github.com/snadboy/docker-revp/commit/7f27432721c800d9d1182527a345122cc8aa68d4))
* implement hosts.yml configuration system with dashboard integration ([df6eed3](https://github.com/snadboy/docker-revp/commit/df6eed38420e242159cd1ac005f5f8a895472631))

# [3.4.0](https://github.com/snadboy/docker-revp/compare/v3.3.0...v3.4.0) (2025-07-23)


### Features

* implement wildcard SSL certificate support with DNS-01 challenge ([672807c](https://github.com/snadboy/docker-revp/commit/672807cad2be49cdf8fd578b1f72a6c9c5e79c46))

# [3.3.0](https://github.com/snadboy/docker-revp/compare/v3.2.0...v3.3.0) (2025-07-21)


### Features

* implement comprehensive static routes CRUD management system ([7ae8b5f](https://github.com/snadboy/docker-revp/commit/7ae8b5fadf82018ae6a48edeca85b680c3827a17))

# [3.2.0](https://github.com/snadboy/docker-revp/compare/v3.1.0...v3.2.0) (2025-07-21)


### Features

* implement reusable SortableResizableTable widget for consistent table behavior ([8c4e627](https://github.com/snadboy/docker-revp/commit/8c4e627881800084ffd9b42a77908b70330bf4ab))

# [3.1.0](https://github.com/snadboy/docker-revp/compare/v3.0.2...v3.1.0) (2025-07-20)


### Features

* implement static routes functionality with YAML configuration ([1bc03e3](https://github.com/snadboy/docker-revp/commit/1bc03e39453145032ca6b6cad13dc969d210f5ab))

## [3.0.2](https://github.com/snadboy/docker-revp/compare/v3.0.1...v3.0.2) (2025-07-20)


### Bug Fixes

* make Docker healthcheck dynamic to API_BIND port configuration ([2be1273](https://github.com/snadboy/docker-revp/commit/2be1273e92cd548890b996d3b36fdb0e6e1809ef))

## [3.0.1](https://github.com/snadboy/docker-revp/compare/v3.0.0...v3.0.1) (2025-07-20)


### Bug Fixes

* improve health check reliability and Docker healthcheck configuration ([038d60b](https://github.com/snadboy/docker-revp/commit/038d60bdc55f3dcc53b78a861b5672c0678821dc))

# [3.0.0](https://github.com/snadboy/docker-revp/compare/v2.0.0...v3.0.0) (2025-07-20)


* refactor\!: combine API_HOST and API_PORT into single API_BIND variable ([45b4d0a](https://github.com/snadboy/docker-revp/commit/45b4d0a1462fbe111fc9c1a54733f2bedb6ec3fc))


### BREAKING CHANGES

* API_HOST and API_PORT environment variables replaced with API_BIND

- Replace separate api_host and api_port configuration with single api_bind
- Use HOST:PORT format consistent with Caddy's CADDY_ADMIN variable
- Add validation to ensure proper HOST:PORT format and valid port range
- Update main.py and app.py to parse api_bind directly
- Remove ssh-debug volume mount and directory (unused debugging feature)
- Update docker-compose.yml, .env files, and README documentation
- Fix healthcheck to use hardcoded localhost:8080

This simplifies configuration and follows standard HOST:PORT convention
used by many services. Users must update their environment variables
from API_HOST/API_PORT to API_BIND format.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

# [2.0.0](https://github.com/snadboy/docker-revp/compare/v1.4.0...v2.0.0) (2025-07-19)


* feat\!: implement multi-port container support with breaking changes ([6867b5d](https://github.com/snadboy/docker-revp/commit/6867b5ded9fc5cd99292dd696d6473113dcede38))


### BREAKING CHANGES

* Label format changed from snadboy.revp.container-port + snadboy.revp.domain to snadboy.revp.{PORT}.{PROPERTY}

- Add ServiceInfo class for individual service configurations within containers
- Redesign ContainerInfo class to support multiple services per container
- Update route management to handle port-based service identification
- Modify Caddy route IDs to include port: revp_route_{container_id}_{port}
- Update containers API to return services array instead of single backend_url
- Enhance dashboard to display multi-port services with proper UI
- Convert docker-compose.yml examples to new port-based label format
- Update README documentation with new label format and examples
- Add CSS styling for service sections in dashboard
- Remove legacy single-service support (no backward compatibility)

Fixes dashboard containers tab showing no entries by updating API structure
to work with new multi-port implementation.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

# [1.4.0](https://github.com/snadboy/docker-revp/compare/v1.3.1...v1.4.0) (2025-07-19)


### Features

* add WebSocket support for containers ([84874b2](https://github.com/snadboy/docker-revp/commit/84874b2210476923d330a501f45607ef65fb00ab))

## [1.3.1](https://github.com/snadboy/docker-revp/compare/v1.3.0...v1.3.1) (2025-07-19)


### Bug Fixes

* correct port mapping and health check for docker-revp ([3b85217](https://github.com/snadboy/docker-revp/commit/3b85217c45f65a0b93f4070885ef0cd757311ee4))

# [1.3.0](https://github.com/snadboy/docker-revp/compare/v1.2.0...v1.3.0) (2025-07-19)


### Features

* add Model Context Protocol (MCP) integration ([5fa4677](https://github.com/snadboy/docker-revp/commit/5fa4677670aa807298dfd628738104de4169aa28))
* improve route management and container reconciliation ([bb8441d](https://github.com/snadboy/docker-revp/commit/bb8441d775e762aa53b09d65ab5e17ac3fe5a0ec))

# [2.0.0](https://github.com/snadboy/docker-revp/compare/v1.2.0...v2.0.0) (2025-07-15)


### BREAKING CHANGES

* Major dashboard redesign with responsive web interface
* Complete table column resizing overhaul with proper behavior
* Comprehensive project documentation added (PRD, API specs, technical docs)
* Cleaned up debugging code and optimized performance


### Features

* **dashboard**: Add complete web-based dashboard with responsive design
* **ui**: Implement proper table column resizing with left-lock, right-fill behavior
* **docs**: Add comprehensive project documentation (PRD, API, technical specs)
* **api**: Enhanced container API with better label handling


### Bug Fixes

* **ui**: Fix table column resizing to only move right border of target column
* **ui**: Remove rightmost column resizer since table now uses full viewport width
* **cleanup**: Remove debugging console.log statements and excessive API logging


# [1.2.0](https://github.com/snadboy/docker-revp/compare/v1.1.1...v1.2.0) (2025-07-15)


### Bug Fixes

* improve table column resizing behavior ([cdd8c17](https://github.com/snadboy/docker-revp/commit/cdd8c17920b29011deb033869c3084bd7edf5068))


### Features

* add containers API endpoint with label defaults ([687b2ed](https://github.com/snadboy/docker-revp/commit/687b2ed2a0c76310c8567db3619ff57afc03341e))

## [1.1.1](https://github.com/snadboy/docker-revp/compare/v1.1.0...v1.1.1) (2025-07-13)


### Bug Fixes

* resolve permission and configuration issues ([87de1b8](https://github.com/snadboy/docker-revp/commit/87de1b8c740b09667950b61b61cdbe26124f21ec))

# [1.1.0](https://github.com/snadboy/docker-revp/compare/v1.0.0...v1.1.0) (2025-07-13)


### Features

* add environment configuration with .env support ([ba4cb2d](https://github.com/snadboy/docker-revp/commit/ba4cb2db60dd2faf4f1bd30402a78a25c039316f))

# 1.0.0 (2025-07-13)


### Features

* initial docker reverse proxy implementation ([38b7673](https://github.com/snadboy/docker-revp/commit/38b767327d57468dd91c91ecf9a0efe9f681ca1c))
