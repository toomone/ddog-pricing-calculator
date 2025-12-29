<script>
	import { Button } from '$lib/components/ui/button';
</script>

<div class="min-h-screen bg-background p-4 md:p-8">
	<div class="mx-auto max-w-3xl">
		<!-- Header with navigation -->
		<div class="mb-6 flex items-center gap-4">
			<Button variant="ghost" href="/" class="gap-2">
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M19 12H5M12 19l-7-7 7-7" />
				</svg>
				Back to Calculator
			</Button>
		</div>

		<!-- FAQ Content -->
		<div class="faq-content">
			<slot />
		</div>

		<!-- Footer -->
		<footer class="mt-8 text-center text-xs text-muted-foreground">
			<p>
				PriceHound Datadog Pricing Calculator uses data sourced from
				<a href="https://www.datadoghq.com/pricing/list/" target="_blank" rel="noopener noreferrer" class="text-datadog-purple hover:underline">
					Datadog Pricing
				</a>
			</p>
		</footer>
	</div>
</div>

<style>
	:global(.faq-content h1) {
		display: block;
		font-size: 1.875rem;
		font-weight: 700;
		margin-bottom: 1.5rem;
		color: hsl(var(--foreground));
	}

	:global(.faq-content h2) {
		display: block;
		font-size: 1.25rem;
		font-weight: 600;
		margin-top: 2rem;
		margin-bottom: 0.75rem;
		color: hsl(var(--foreground));
	}

	:global(.faq-content p) {
		display: block;
		margin-bottom: 1rem;
		line-height: 1.7;
		color: hsl(var(--muted-foreground));
	}

	:global(.faq-content ul) {
		display: block;
		list-style-type: disc;
		padding-left: 1.5rem;
		margin-bottom: 1rem;
	}

	:global(.faq-content li) {
		display: list-item;
		margin-bottom: 0.5rem;
		line-height: 1.6;
		color: hsl(var(--muted-foreground));
	}

	:global(.faq-content strong) {
		color: hsl(var(--foreground));
		font-weight: 600;
	}

	:global(.faq-content a) {
		color: hsl(270 60% 50%);
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	:global(.faq-content a:hover) {
		opacity: 0.8;
	}
</style>

