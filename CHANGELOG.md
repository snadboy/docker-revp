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
