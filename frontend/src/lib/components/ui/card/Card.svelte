<script lang="ts">
	import { cn } from '$lib/utils';

	let className: string | undefined = undefined;
	export { className as class };
</script>

<div
	class={cn(
		'rounded-2xl border-2 border-border/50 bg-card text-card-foreground shadow-xl backdrop-blur-sm',
		className
	)}
	{...$$restProps}
>
	<slot />
</div>

