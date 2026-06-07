package pipeline

import (
    "crypto/sha256"
    "encoding/hex"
    "sync"
)

type DataBlock struct {
    ID   string
    Raw  []byte
    Hash string
}

func hashWorker(id int, blocks <-chan DataBlock, results chan<- DataBlock, wg *sync.WaitGroup) {
    defer wg.Done()
    for block := range blocks {
        hasher := sha256.New()
        hasher.Write(block.Raw)
        block.Hash = hex.EncodeToString(hasher.Sum(nil))
        results <- block
    }
}

func ProcessStream(inputs []DataBlock, workerCount int) map[string]string {
    blocksChan := make(chan DataBlock, len(inputs))
    resultsChan := make(chan DataBlock, len(inputs))
    var wg sync.WaitGroup

    for i := 0; i < workerCount; i++ {
        wg.Add(1)
        go hashWorker(i, blocksChan, resultsChan, &wg)
    }

    for _, input := range inputs {
        blocksChan <- input
    }
    close(blocksChan)

    go func() {
        wg.Wait()
        close(resultsChan)
    }()

    hashMap := make(map[string]string)
    for result := range resultsChan {
        hashMap[result.ID] = result.Hash
    }

    return hashMap
}