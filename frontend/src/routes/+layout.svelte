<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner';
</script>

<ModeWatcher />
<Toaster position="top-right" richColors />
<div class="gradient-bg min-h-screen">
	<slot />
</div>

