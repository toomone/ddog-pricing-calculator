<script lang="ts">
	import { cn } from '$lib/utils';

	let className: string | undefined = undefined;
	export { className as class };
</script>

<div
	class={cn(
		'rounded border border-border/50 bg-card text-card-foreground shadow-sm',
		className
	)}
	{...$$restProps}
>
	<slot />
</div>

