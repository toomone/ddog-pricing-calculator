<script lang="ts">
	import { Toaster as Sonner } from 'svelte-sonner';
	import { mode } from 'mode-watcher';
</script>

<Sonner
	theme={$mode}
	class="toaster group"
	toastOptions={{
		classes: {
			toast: 'group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg',
			description: 'group-[.toast]:text-muted-foreground',
			actionButton: 'group-[.toast]:bg-primary group-[.toast]:text-primary-foreground',
			cancelButton: 'group-[.toast]:bg-muted group-[.toast]:text-muted-foreground',
			success: 'group-[.toaster]:bg-background group-[.toaster]:text-datadog-green group-[.toaster]:border-datadog-green/30',
			error: 'group-[.toaster]:bg-background group-[.toaster]:text-destructive group-[.toaster]:border-destructive/30',
			info: 'group-[.toaster]:bg-background group-[.toaster]:text-datadog-blue group-[.toaster]:border-datadog-blue/30'
		}
	}}
	{...$$restProps}
/>

