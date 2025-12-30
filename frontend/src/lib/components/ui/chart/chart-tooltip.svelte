<script lang="ts">
	import { cn } from "$lib/utils";

	export let hideLabel: boolean = false;
	let className: string | undefined = undefined;
	export { className as class };
</script>

<div
	class={cn(
		"rounded-lg border border-border bg-card px-3 py-2 text-sm shadow-lg",
		className
	)}
>
	<slot />
</div>

