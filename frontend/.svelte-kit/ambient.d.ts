
// this file is generated — do not edit it


/// <reference types="@sveltejs/kit" />

/**
 * Environment variables [loaded by Vite](https://vitejs.dev/guide/env-and-mode.html#env-files) from `.env` files and `process.env`. Like [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), this module cannot be imported into client-side code. This module only includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured).
 * 
 * _Unlike_ [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), the values exported from this module are statically injected into your bundle at build time, enabling optimisations like dead code elimination.
 * 
 * ```ts
 * import { API_KEY } from '$env/static/private';
 * ```
 * 
 * Note that all environment variables referenced in your code should be declared (for example in an `.env` file), even if they don't have a value until the app is deployed:
 * 
 * ```
 * MY_FEATURE_FLAG=""
 * ```
 * 
 * You can override `.env` values from the command line like so:
 * 
 * ```sh
 * MY_FEATURE_FLAG="enabled" npm run dev
 * ```
 */
declare module '$env/static/private' {
	export const _ZO_DOCTOR: string;
	export const rvm_use_flag: string;
	export const rvm_bin_path: string;
	export const VSCODE_CRASH_REPORTER_PROCESS_TYPE: string;
	export const NODE: string;
	export const INIT_CWD: string;
	export const rvm_ruby_alias: string;
	export const rvm_quiet_flag: string;
	export const rvm_gemstone_url: string;
	export const TERM: string;
	export const SHELL: string;
	export const VSCODE_PROCESS_TITLE: string;
	export const rvm_docs_type: string;
	export const TMPDIR: string;
	export const HOMEBREW_REPOSITORY: string;
	export const npm_config_global_prefix: string;
	export const ORIGINAL_XDG_CURRENT_DESKTOP: string;
	export const MallocNanoZone: string;
	export const CURSOR_TRACE_ID: string;
	export const COLOR: string;
	export const rvm_hook: string;
	export const NO_COLOR: string;
	export const npm_config_noproxy: string;
	export const npm_config_local_prefix: string;
	export const USER: string;
	export const rvm_user_flag: string;
	export const rvm_gemstone_package_file: string;
	export const COMMAND_MODE: string;
	export const npm_config_globalconfig: string;
	export const rvm_path: string;
	export const SSH_AUTH_SOCK: string;
	export const __CF_USER_TEXT_ENCODING: string;
	export const npm_execpath: string;
	export const rvm_proxy: string;
	export const rvm_ruby_global_gems_path: string;
	export const rvm_ruby_file: string;
	export const rvm_sticky_flag: string;
	export const rvm_silent_flag: string;
	export const rvm_prefix: string;
	export const rvm_ruby_make: string;
	export const PATH: string;
	export const npm_package_json: string;
	export const _: string;
	export const npm_config_userconfig: string;
	export const npm_config_init_module: string;
	export const __CFBundleIdentifier: string;
	export const npm_command: string;
	export const PWD: string;
	export const VSCODE_HANDLES_UNCAUGHT_ERRORS: string;
	export const npm_lifecycle_event: string;
	export const EDITOR: string;
	export const VSCODE_ESM_ENTRYPOINT: string;
	export const P9K_SSH: string;
	export const npm_package_name: string;
	export const rvm_system_flag: string;
	export const rvm_sdk: string;
	export const CURSOR_AGENT: string;
	export const npm_config_npm_version: string;
	export const XPC_FLAGS: string;
	export const FORCE_COLOR: string;
	export const npm_config_node_gyp: string;
	export const npm_package_version: string;
	export const XPC_SERVICE_NAME: string;
	export const rvm_version: string;
	export const rvm_script_name: string;
	export const rvm_pretty_print_flag: string;
	export const SHLVL: string;
	export const HOME: string;
	export const rvm_ruby_mode: string;
	export const VSCODE_NLS_CONFIG: string;
	export const rvm_ruby_string: string;
	export const HOMEBREW_PREFIX: string;
	export const rvm_ruby_configure: string;
	export const rvm_ruby_url: string;
	export const npm_config_cache: string;
	export const LOGNAME: string;
	export const npm_lifecycle_script: string;
	export const rvm_alias_expanded: string;
	export const COMPOSER_NO_INTERACTION: string;
	export const VSCODE_IPC_HOOK: string;
	export const VSCODE_CODE_CACHE_PATH: string;
	export const npm_config_user_agent: string;
	export const rvm_nightly_flag: string;
	export const rvm_file_name: string;
	export const VSCODE_PID: string;
	export const rvm_ruby_make_install: string;
	export const INFOPATH: string;
	export const HOMEBREW_CELLAR: string;
	export const rvm_niceness: string;
	export const rvm_delete_flag: string;
	export const rvm_ruby_bits: string;
	export const rvm_bin_flag: string;
	export const rvm_only_path_flag: string;
	export const VSCODE_L10N_BUNDLE_LOCATION: string;
	export const VSCODE_CWD: string;
	export const npm_node_execpath: string;
	export const npm_config_prefix: string;
	export const NODE_ENV: string;
}

/**
 * Similar to [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private), except that it only includes environment variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`), and can therefore safely be exposed to client-side code.
 * 
 * Values are replaced statically at build time.
 * 
 * ```ts
 * import { PUBLIC_BASE_URL } from '$env/static/public';
 * ```
 */
declare module '$env/static/public' {
	
}

/**
 * This module provides access to runtime environment variables, as defined by the platform you're running on. For example if you're using [`adapter-node`](https://github.com/sveltejs/kit/tree/main/packages/adapter-node) (or running [`vite preview`](https://svelte.dev/docs/kit/cli)), this is equivalent to `process.env`. This module only includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured).
 * 
 * This module cannot be imported into client-side code.
 * 
 * ```ts
 * import { env } from '$env/dynamic/private';
 * console.log(env.DEPLOYMENT_SPECIFIC_VARIABLE);
 * ```
 * 
 * > [!NOTE] In `dev`, `$env/dynamic` always includes environment variables from `.env`. In `prod`, this behavior will depend on your adapter.
 */
declare module '$env/dynamic/private' {
	export const env: {
		_ZO_DOCTOR: string;
		rvm_use_flag: string;
		rvm_bin_path: string;
		VSCODE_CRASH_REPORTER_PROCESS_TYPE: string;
		NODE: string;
		INIT_CWD: string;
		rvm_ruby_alias: string;
		rvm_quiet_flag: string;
		rvm_gemstone_url: string;
		TERM: string;
		SHELL: string;
		VSCODE_PROCESS_TITLE: string;
		rvm_docs_type: string;
		TMPDIR: string;
		HOMEBREW_REPOSITORY: string;
		npm_config_global_prefix: string;
		ORIGINAL_XDG_CURRENT_DESKTOP: string;
		MallocNanoZone: string;
		CURSOR_TRACE_ID: string;
		COLOR: string;
		rvm_hook: string;
		NO_COLOR: string;
		npm_config_noproxy: string;
		npm_config_local_prefix: string;
		USER: string;
		rvm_user_flag: string;
		rvm_gemstone_package_file: string;
		COMMAND_MODE: string;
		npm_config_globalconfig: string;
		rvm_path: string;
		SSH_AUTH_SOCK: string;
		__CF_USER_TEXT_ENCODING: string;
		npm_execpath: string;
		rvm_proxy: string;
		rvm_ruby_global_gems_path: string;
		rvm_ruby_file: string;
		rvm_sticky_flag: string;
		rvm_silent_flag: string;
		rvm_prefix: string;
		rvm_ruby_make: string;
		PATH: string;
		npm_package_json: string;
		_: string;
		npm_config_userconfig: string;
		npm_config_init_module: string;
		__CFBundleIdentifier: string;
		npm_command: string;
		PWD: string;
		VSCODE_HANDLES_UNCAUGHT_ERRORS: string;
		npm_lifecycle_event: string;
		EDITOR: string;
		VSCODE_ESM_ENTRYPOINT: string;
		P9K_SSH: string;
		npm_package_name: string;
		rvm_system_flag: string;
		rvm_sdk: string;
		CURSOR_AGENT: string;
		npm_config_npm_version: string;
		XPC_FLAGS: string;
		FORCE_COLOR: string;
		npm_config_node_gyp: string;
		npm_package_version: string;
		XPC_SERVICE_NAME: string;
		rvm_version: string;
		rvm_script_name: string;
		rvm_pretty_print_flag: string;
		SHLVL: string;
		HOME: string;
		rvm_ruby_mode: string;
		VSCODE_NLS_CONFIG: string;
		rvm_ruby_string: string;
		HOMEBREW_PREFIX: string;
		rvm_ruby_configure: string;
		rvm_ruby_url: string;
		npm_config_cache: string;
		LOGNAME: string;
		npm_lifecycle_script: string;
		rvm_alias_expanded: string;
		COMPOSER_NO_INTERACTION: string;
		VSCODE_IPC_HOOK: string;
		VSCODE_CODE_CACHE_PATH: string;
		npm_config_user_agent: string;
		rvm_nightly_flag: string;
		rvm_file_name: string;
		VSCODE_PID: string;
		rvm_ruby_make_install: string;
		INFOPATH: string;
		HOMEBREW_CELLAR: string;
		rvm_niceness: string;
		rvm_delete_flag: string;
		rvm_ruby_bits: string;
		rvm_bin_flag: string;
		rvm_only_path_flag: string;
		VSCODE_L10N_BUNDLE_LOCATION: string;
		VSCODE_CWD: string;
		npm_node_execpath: string;
		npm_config_prefix: string;
		NODE_ENV: string;
		[key: `PUBLIC_${string}`]: undefined;
		[key: `${string}`]: string | undefined;
	}
}

/**
 * Similar to [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), but only includes variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`), and can therefore safely be exposed to client-side code.
 * 
 * Note that public dynamic environment variables must all be sent from the server to the client, causing larger network requests — when possible, use `$env/static/public` instead.
 * 
 * ```ts
 * import { env } from '$env/dynamic/public';
 * console.log(env.PUBLIC_DEPLOYMENT_SPECIFIC_VARIABLE);
 * ```
 */
declare module '$env/dynamic/public' {
	export const env: {
		[key: `PUBLIC_${string}`]: string | undefined;
	}
}
