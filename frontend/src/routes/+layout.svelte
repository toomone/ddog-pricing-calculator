<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { PUBLIC_DD_ENV } from '$env/static/public';
	import { APP_VERSION } from '$lib/version';

	onMount(() => {
		if (browser) {
			import('@datadog/browser-rum').then(({ datadogRum }) => {
				datadogRum.init({
					applicationId: 'c109fa30-3a43-4ce1-8679-88ae77369152',
					clientToken: 'pub38efae98b117027f1be52a7ed202072b',
					site: 'datadoghq.com',
					service: 'pricehound',
					env: PUBLIC_DD_ENV || 'prod',
					version: APP_VERSION,
					sessionSampleRate: 100,
					sessionReplaySampleRate: 100,
					trackBfcacheViews: true,
					defaultPrivacyLevel: 'allow',
				});
			});
		}
	});
</script>

<ModeWatcher />
<Toaster position="top-right" richColors />
<div class="gradient-bg min-h-screen">
	<slot />
</div>

